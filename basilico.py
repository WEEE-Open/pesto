#!/usr/bin/env python
import json
import subprocess
import stat
import os
import sys
import time
from collections import deque
from typing import Optional, Callable, Dict, Set, List

from pytarallo import Tarallo, Errors
from dotenv import load_dotenv
from io import StringIO

from pytarallo.Errors import ValidationError, NotAuthorizedError
from pytarallo.ItemToUpload import ItemToUpload
from twisted.internet import reactor, protocol
from twisted.protocols.basic import LineOnlyReceiver
import threading
import logging
from datetime import datetime

from read_smartctl import extract_smart_data, smart_health_status, parse_single_disk

NAME = "basilico"
# Use env vars, do not change the value here
TEST_MODE = False


class Disk:
    def __init__(self, lsblk, tarallo: Optional[Tarallo.Tarallo]):
        self._lsblk = lsblk
        if "path" not in self._lsblk:
            raise RuntimeError("lsblk did not provide path for this disk: " + self._lsblk)
        self._path = str(self._lsblk["path"])
        self._mountpoint_map = self._lsblk["mountpoint_map"]
        del self._lsblk["mountpoint_map"]

        self._composite_id = Disk.make_composite_id(self._lsblk)
        self._code = None
        self._item = None

        self._update_lock = threading.Lock()
        self._queue_lock = threading.Lock()
        self._commands_queue = deque()

        self._tarallo = tarallo
        self._get_code(False)
        self._get_item()

    def update_mountpoints(self):
        with self._update_lock:
            # lsblk 2 is like Despacito 2
            lsblk2 = get_disks(self._path)
            for one_disk in lsblk2:
                if one_disk.get("path") == self._path:
                    self._lsblk["mountpoint"] = one_disk.get("mountpoint", [])
                    self._mountpoint_map = one_disk.get("mountpoint_map", {})
                    # This is not copied over again
                    # if "mountpoint_map" in self._lsblk:
                    #     del self._lsblk["mountpoint_map"]
                    break

    def get_mountpoints_map(self) -> dict:
        # Probably pointless lock
        with self._update_lock:
            return self._mountpoint_map

    @staticmethod
    def make_composite_id(lsblk: dict):
        return lsblk.get("path"), lsblk.get("wwn"), lsblk.get("serial")

    def compare_composite_id(self, lsblk_other: dict):
        return self._composite_id == self.make_composite_id(lsblk_other)

    def queue_is_empty(self):
        with self._queue_lock:
            return len(self._commands_queue) == 0

    def enqueue(self, cmd_runner):
        cmd_runner: CommandRunner
        with self._queue_lock:
            self._commands_queue.append(cmd_runner)
            if len(self._commands_queue) == 1:
                cmd_runner.start()

    def dequeue(self, cmd_runner):
        cmd_runner: CommandRunner
        with self._queue_lock:
            try:
                self._commands_queue.remove(cmd_runner)
            except ValueError:
                # TODO: This could be a return
                pass
            if len(self._commands_queue) > 0:
                next_in_line: CommandRunner = self._commands_queue[0]
                if not next_in_line.is_alive():
                    next_in_line.start()
            else:
                if cmd_runner.get_cmd() != "queued_sleep":
                    cmd_runner._call_hdparm_for_sleep(self._path)

    def get_path(self):
        return self._path

    def update_from_tarallo_if_needed(self) -> bool:
        changes = False
        if not self._code:
            old_code = self._code
            self._get_code(True)
            changes = self._code == old_code
        self._get_item()
        return changes

    def serialize_disk(self):
        result = self._lsblk
        result["code"] = self._code
        critical = False
        if not TEST_MODE:
            for mountpoint in self._lsblk["mountpoint"]:
                if mountpoint != "[SWAP]":
                    critical = True
                    break
        result["has_critical_mounts"] = critical
        return result

    def update_status(self, status: str) -> bool:
        if self._tarallo and self._code:
            self._tarallo.update_item_features(self._code, {"smart-data": status})
            return True
        return False

    def update_erase(self, erased: bool, all_blocks_ok: Optional[bool]) -> bool:
        if self._tarallo and self._code:
            data = {}
            # Can be True, False or None
            if all_blocks_ok is not None:
                data["surface-scan"] = "pass" if all_blocks_ok else "fail"
            if erased:
                data["data-erased"] = "yes"
                data["software"] = None

            if len(data) > 0:
                self._tarallo.update_item_features(self._code, data)
            return True
        return False

    def update_software(self, software: str) -> bool:
        if self._tarallo and self._code:
            data = {"software": software}

            self._tarallo.update_item_features(self._code, data)
            return True
        return False

    def _get_code(self, stop_on_error: bool = True):
        if not self._tarallo:
            if TEST_MODE:
                import binascii

                num = binascii.crc32(self._path.encode("utf-8")) % 300
                if num % 2:
                    self._code = "H" + str(num)
                else:
                    self._code = None
            else:
                self._code = None
            return
        if "serial" not in self._lsblk:
            self._code = None
            if stop_on_error:
                raise ErrorThatCanBeManuallyFixed(f"Disk {self._path} has no serial number")

        sn = self._lsblk["serial"]
        sn: str
        if sn and sn.startswith("WD-"):
            sn = sn[3:]

        try:
            codes = self._tarallo.get_codes_by_feature("sn", sn)
            if len(codes) <= 0:
                self._code = None
                logging.debug(f"Disk {sn} not found in tarallo")
            elif len(codes) == 1:
                self._code = codes[0]
                logging.debug(f"Disk {sn} found as {self._code}")
            else:
                self._code = None
                if stop_on_error:
                    raise ErrorThatCanBeManuallyFixed(f"Duplicate codes for {self._path}: {' '.join(codes)}, S/N is {sn}")
        except Errors.NoInternetConnectionError:
            self._code = None
            if stop_on_error:
                raise ErrorThatCanBeManuallyFixed(f"Tarallo lookup for disk with S/N {sn} failed due to a connection error")
        except Errors.ServerError:
            self._code = None
            if stop_on_error:
                raise ErrorThatCanBeManuallyFixed(f"Tarallo lookup for disk with S/N {sn} failed due to server error, try again later")
        except Errors.AuthenticationError:
            self._code = None
            if stop_on_error:
                raise ErrorThatCanBeManuallyFixed(f"Tarallo lookup for disk with S/N {sn} failed due to authentication error, check the token")
        except (Errors.ValidationError, RuntimeError) as e:
            self._code = None
            logging.warning(f"Tarallo lookup failed unexpectedly for disk with S/N {sn}", exc_info=e)
            if stop_on_error:
                raise ErrorThatCanBeManuallyFixed(f"Tarallo lookup for disk with S/N {sn} failed, more info has been logged on the server")

    def _get_item(self):
        if self._tarallo and self._code:
            # Nothing to do, only the code is used at the moment. Add a try-except if you uncomment.
            # self._item = self._tarallo.get_item(self._code, 0)
            pass
        else:
            self._item = None

    def create_on_tarallo(self, features: dict, loc: str = None) -> Optional[str]:
        # TODO: does this need any lock?
        # with self._update_lock:
        if self._tarallo:
            disk = ItemToUpload()
            for f, v in features.items():
                disk.features[f] = v
            disk.set_parent(loc)
            success = self._tarallo.add_item(disk)
            if success and isinstance(disk.code, str) and disk.code != "":
                return disk.code
            # success = self._tarallo.bulk_add(disk.serializable())
        return None

    def set_code(self, code: str):
        self._code = code


class SudoSessionKeeper(threading.Thread):
    def run(self):
        while True:
            process = subprocess.run(["sudo", "-nv"])
            threading.Event().wait(241)


class ErrorThatCanBeManuallyFixed(Exception):
    pass


class CommandRunner(threading.Thread):
    def __init__(self, cmd: str, args: str, the_id: int):
        threading.Thread.__init__(self)
        self._cmd = cmd
        self._args = args
        self._the_id = the_id
        self._go = True
        self._queued_command = None

        self._function, disk_for_queue = self.dispatch_command(cmd, args)
        if not self._function:
            self.send_msg("error", {"message": "Unrecognized command", "command": cmd})
            self._function = None
            return
        self._queued_command = None
        if disk_for_queue is not None:  # Empty string must enter this branch
            # No need to lock, disks are never deleted, so if it is found then it is valid
            disk = disks.get(disk_for_queue, None)
            if not disk:
                self.send_msg("error", {"message": f"{args} is not a disk"})
                self._function = None
                return
            # Do not start yet, just prepare the data structure
            self._queued_command = QueuedCommand(disk, self)

            # And enqueue, which will start it when needed
            with queued_commands_lock:
                disk.enqueue(self)
        else:
            # Start immediately
            self.start()

    # noinspection PyUnresolvedReferences
    def started(self) -> bool:
        return self._started.is_set()

    def get_cmd(self):
        return self._cmd

    def get_queued_command(self):
        return self._queued_command

    def run(self):
        try:
            # Stop immediately if nothing was dispatched
            if not self._function:
                self._queued_command.notify_error("Unknown command")
                self._queued_command.delete_when_done()
                return
            # Also stop if program is terminating
            if not self._go:
                return

            # Otherwise, lessss goooooo!
            with running_commands_lock:
                running_commands.add(self)

            try:
                self._function(self._cmd, self._args)
            except Exception as e:
                logging.error(f"[{self._the_id}] BIG ERROR in command thread", exc_info=e)
        finally:
            # The next thread on the disk can start, if there's a queue
            if self._queued_command:
                # Notify finish only if not already notified, as a catch all for errors
                # that may prevent the actual function from notifying
                self._queued_command.notify_finish_safe()
                self._queued_command.disk.dequeue(self)
            # Not running anymore (in a few nanoseconds, anyway)
            with running_commands_lock:
                try:
                    # If the thread was never started (not self._go and similar), it won't be there
                    running_commands.remove(self)
                except KeyError:
                    pass

    def stop_asap(self):
        # This is completely pointless unless the command checks self._go
        # (none of them does, for now)
        self._go = False

    def dispatch_command(self, cmd: str, args: str) -> (Optional[Callable[[str, str], None]], Optional[str]):
        commands = {
            "sudo_password": self.sudo_password,
            "smartctl": self.get_smartctl,
            "queued_smartctl": self.queued_get_smartctl,
            "queued_badblocks": self.badblocks,
            "queued_cannolo": self.cannolo,
            "queued_sleep": self.sleep,
            "queued_umount": self.umount,
            "upload_to_tarallo": self.upload_to_tarallo,
            "queued_upload_to_tarallo": self.queued_upload_to_tarallo,
            "get_disks": self.get_disks,
            "ping": self.ping,
            "close_at_end": self.close_at_end,
            "get_queue": self.get_queue,
            "remove": self.remove_one_from_queue,
            "remove_all": self.remove_all_from_queue,
            "remove_completed": self.remove_all_from_queue,
            "remove_queued": self.remove_all_from_queue,
            "list_iso": self.list_iso,
            "stop": self.stop_process,
        }
        logging.debug(f"[{self._the_id}] Received command {cmd}{' with args' if len(args) > 0 else ''}")
        if cmd.startswith("queued_"):
            disk_for_queue = self.dev_from_args(args)
        else:
            disk_for_queue = None

        return commands.get(cmd.lower(), None), disk_for_queue

    # noinspection PyUnusedLocal
    def get_queue(self, cmd: str, args: str):
        param = []
        with queued_commands_lock:
            for queued_command in queued_commands:
                queued_command.lock_notifications()
                param.append(queued_command.serialize_me())
            self.send_msg(cmd, param)
            for queued_command in queued_commands:
                queued_command.unlock_notifications()

    @staticmethod
    def dev_from_args(args: str):
        # This may be more complicated for some future commands
        return args.split(" ", 1)[0]

    def list_iso(self, cmd: str, iso_dir: str):
        files = []
        try:
            for file in os.listdir(iso_dir):
                if file.startswith("."):
                    continue
                files.append(os.path.join(iso_dir, file))
        except FileNotFoundError:
            self.send_msg(
                "error",
                {"message": f"ISO directory {iso_dir} does not exist on server"},
            )
            return
        except NotADirectoryError:
            self.send_msg(
                "error",
                {"message": f"Cannot read {iso_dir} on server: is not a directory"},
            )
            return
        except PermissionError:
            self.send_msg(
                "error",
                {"message": f"Cannot read {iso_dir} on server: permission denied"},
            )
            return
        except Exception as e:
            self.send_msg(
                "error",
                {"message": f"Cannot list files in iso dir {iso_dir}: {str(e)}"},
            )
            return
        self.send_msg(cmd, files)

    # noinspection PyMethodMayBeStatic
    def remove_all_from_queue(self, cmd: str, _unused: str):
        remove_completed = False
        remove_scheduled = False
        if cmd == "remove_completed":
            remove_completed = True
        elif cmd == "remove_queued":
            remove_scheduled = True
        else:
            remove_completed = True
            remove_scheduled = True
        logging.debug(f"remove_completed = {remove_completed}, remove_scheduled = {remove_scheduled}")

        with queued_commands_lock:
            with running_commands_lock:
                commands_to_remove = []

                for the_command in queued_commands:
                    if the_command.command_runner.started():
                        if not the_command.command_runner.is_alive():
                            if remove_completed:
                                commands_to_remove.append(the_command)
                    else:
                        if remove_scheduled:
                            commands_to_remove.append(the_command)

                for the_command in commands_to_remove:
                    queued_commands.remove(the_command)
                logging.debug(f"Removed {len(commands_to_remove)} items from tasks list")

        return None

    # noinspection PyMethodMayBeStatic
    def remove_one_from_queue(self, _cmd: str, queue_id: str):
        for the_cmd in queued_commands:
            if the_cmd.id_is(queue_id):
                the_cmd.delete_when_done()
                break
        return None

    def badblocks(self, _cmd: str, dev: str):
        go_ahead = self._unswap()
        if not go_ahead:
            return

        self._queued_command.notify_start("Running badblocks")
        if TEST_MODE:
            final_message = ""
            for progress in range(0, 100, 10):
                if self._go:
                    self._queued_command.notify_percentage(progress, f"{progress/10} errors")
                    threading.Event().wait(2)
                else:
                    final_message = "Process interrupted by user."
                if progress == 100:
                    final_message = f"Finished with {progress/10} errors!"

            completed = True
            all_ok = False
        else:
            custom_env = os.environ.copy()
            custom_env["LC_ALL"] = "C"

            pipe = subprocess.Popen(
                (
                    "sudo",
                    "-n",
                    "badblocks",
                    "-w",
                    "-s",
                    "-p",
                    "0",
                    "-t",
                    "0x00",
                    "-b",
                    "4096",
                    dev,
                ),
                stderr=subprocess.PIPE,
                env=custom_env,
            )  # , stdout=subprocess.PIPE)

            percent = 0.0
            reading_and_comparing = False
            errors = -1
            deleting = False
            buffer = bytearray()
            for char in iter(lambda: pipe.stderr.read(1), b""):
                if not self._go:
                    pipe.kill()
                    pipe.wait()
                    print(f"Killed badblocks process {self.get_queued_command().id()}")
                    self._queued_command.notify_finish_with_error("Process terminated by user.")
                    return
                if char == b"":
                    if pipe.poll() is not None:
                        break
                elif char == b"\b":
                    if not deleting:
                        result = buffer.decode("utf-8")
                        errors_print = "?"

                        reading_and_comparing = reading_and_comparing or ("Reading and comparing" in result)

                        # If other messages are printed, ignore them
                        i = result.index("% done")
                        if i >= 0:
                            # /2 due to the 0x00 test + read & compare
                            percent = float(result[i - 6 : i]) / 2
                            if reading_and_comparing:
                                percent += 50
                            i = result.index("(", i)
                            if i >= 0:
                                # errors_str = result[i+1:].split(")", 1)[0]
                                errors_str = result[i + 1 :].split(" ", 1)[0]
                                # The errors are read, write and corruption
                                errors_str = errors_str.split("/")
                                errors = 0  # badblocks prints the 3 totals every time
                                for error in errors_str:
                                    errors += int(error)
                                errors_print = str(errors)
                            self._queued_command.notify_percentage(percent, f"{errors_print} errors")
                        buffer.clear()
                        deleting = True
                # elif char == b'\n':
                #     # Skip the first lines (total number of blocks)
                #     buffer.clear()
                else:
                    if deleting:
                        deleting = False
                    buffer += char

            # TODO: was this needed? Why were we doing it twice?
            # pipe.wait()
            exitcode = pipe.wait()

            if errors <= -1:
                all_ok = None
                errors_print = "an unknown amount of"
            elif errors == 0:
                all_ok = True
                errors_print = "no"
            else:
                all_ok = False
                errors_print = str(errors)
            final_message = f"Finished with {errors_print} errors"

            if exitcode == 0:
                # self._queued_command.notify_finish(final_message)
                completed = True
            else:
                self._queued_command.notify_error()
                final_message += f" and badblocks exited with status {exitcode}"
                # self._queued_command.notify_finish(final_message)
                completed = False

            # print(pipe.stdout.readline().decode('utf-8'))
            # print(pipe.stderr.readline().decode('utf-8'))

        with disks_lock:
            update_disks_if_needed(self)
            disk_ref = disks[dev]

        # noinspection PyBroadException
        try:
            disk_ref.update_erase(completed, all_ok)
        except Exception as e:
            final_message = f"Error during upload. {final_message}"
            self._queued_command.notify_error(final_message)
            logging.warning(
                f"[{self._the_id}] Can't update badblocks results of {dev} on tarallo",
                exc_info=e,
            )
        self._queued_command.notify_finish(final_message)

    def ping(self, _cmd: str, _nothing: str):
        self.send_msg("pong", None)

    # noinspection PyMethodMayBeStatic
    def close_at_end(self, _cmd: str, _nothing: str):
        logging.info("Server will close at end")
        with CLOSE_AT_END_LOCK:
            global CLOSE_AT_END
            # Do not start the timer twice
            if CLOSE_AT_END:
                return
            CLOSE_AT_END = True
        # noinspection PyUnresolvedReferences
        reactor.callFromThread(reactor.callLater, CLOSE_AT_END_TIMER, try_stop_at_end)

    @staticmethod
    def _get_last_linux_partition_path_and_number(dev: str) -> tuple[str, str] | tuple[None, None]:
        # Use PTTYPE to get MBR/GPT (dos/gpt are the possible values)
        # PARTTYPENAME could be useful, too
        output = subprocess.getoutput(f"lsblk -o PATH,PARTN,PARTTYPE -J {dev}")
        jsonized = json.loads(output)
        return CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(jsonized)

    @staticmethod
    def _get_last_linux_partition_path_and_number_from_lsblk(lsblk_json: dict) -> tuple[str, str] | tuple[None, None]:
        for i, entry in enumerate(lsblk_json["blockdevices"]):
            if entry["path"]:  # lsblk also returns the device itself, which has no partitions
                # GPT or MBR Linux partition ID
                if entry["parttype"] == "0fc63daf-8483-4772-8e79-3d69d8477de4" or entry["parttype"] == "0x83":
                    return entry["path"], (entry["partn"] if "partn" in entry else i)
        return None, None

    def cannolo(self, _cmd: str, dev_and_iso: str):
        parts: list[Optional[str]] = dev_and_iso.split(" ", 1)
        while len(parts) < 2:
            parts.append(None)
        dev, iso = parts
        if iso is None:
            self._queued_command.notify_finish_with_error(f"No iso selected")
            return

        if not os.path.exists(iso):
            self._queued_command.notify_finish_with_error(f"File {iso} does not exist")
            return

        if not os.path.isfile(iso):
            self._queued_command.notify_finish_with_error(f"{iso} is not a file (is it a directory?)")
            return

        go_ahead = self._unswap()
        if not go_ahead:
            return

        success = True

        self._queued_command.notify_start("Cannoling")
        if TEST_MODE:
            self._queued_command.notify_percentage(10)
            threading.Event().wait(2)
            self._queued_command.notify_percentage(20)
            threading.Event().wait(2)
            self._queued_command.notify_percentage(30)
            threading.Event().wait(2)
            self._queued_command.notify_percentage(40)
            threading.Event().wait(2)
            self._queued_command.notify_percentage(50)
            threading.Event().wait(2)
            self._queued_command.notify_percentage(60)
            threading.Event().wait(2)
            self._queued_command.notify_percentage(70)
            threading.Event().wait(2)
            self._queued_command.notify_percentage(80)
            threading.Event().wait(2)
            self._queued_command.notify_percentage(90)
            threading.Event().wait(2)
        else:
            success = self.dd(iso, dev)
            if success:
                part_path, part_number = self._get_last_linux_partition_path_and_number(dev)

                success = run_command_on_partition(dev, f"sudo growpart {dev} {part_number}")
                if success:
                    success = run_command_on_partition(dev, f"sudo e2fsck -fy {part_path}")
                    if success:
                        success = run_command_on_partition(dev, f"sudo resize2fs {part_path}")
                        if success:
                            pass
                        else:
                            self._queued_command.notify_error(f"resize2fs failed")
                    else:
                        self._queued_command.notify_error(f"e2fsck failed")
                else:
                    self._queued_command.notify_error(f"growpart failed")
            else:
                self._queued_command.notify_error(f"Disk imaging failed")

        if success:
            with disks_lock:
                update_disks_if_needed(self)
                disk_ref = disks[dev]

            pretty_iso = self._pretty_print_iso(iso)
            self._queued_command.notify_percentage(100.0, f"{pretty_iso} installed!")

            final_message = f"{pretty_iso} installed, Tarallo updated"
            # noinspection PyBroadException
            try:
                disk_ref.update_software(pretty_iso)
            except Exception as e:
                final_message = f"{pretty_iso} installed, failed to update Tarallo"
                self._queued_command.notify_error(f"{pretty_iso} installed, failed to update Tarallo")
                logging.warning(
                    f"[{self._the_id}] Can't update software of {dev} on tarallo",
                    exc_info=e,
                )
            self._queued_command.notify_finish(final_message)
        else:
            self._queued_command.notify_finish()

    def umount(self, _cmd: str, dev: str):
        self._queued_command.notify_start("Calling umount")
        success = self._umount_internal(dev)
        self._queued_command.disk.update_mountpoints()
        if success:
            self._queued_command.notify_finish(f"Disk {dev} umounted")
        else:
            self._queued_command.notify_finish_with_error(f"umount failed")

    def _umount_internal(self, dev):
        try:
            result = subprocess.run(["lsblk", "-J", dev], capture_output=True, text=True)

            if result.returncode != 0:
                return False

            lsblk_output = json.loads(result.stdout)

            partitions_to_unmount = []
            blockdevices = lsblk_output.get("blockdevices", [])
            for device in blockdevices:
                if "children" in device:
                    for partition in device["children"]:
                        if "mountpoints" in partition and len(partition["mountpoints"]) > 0:
                            partitions_to_unmount.append(f"/dev/{partition['name']}")
                    break

            if not partitions_to_unmount:
                return True

            for partition in partitions_to_unmount:
                rc = self._call_shell_command(("sudo", "umount", partition))

                if rc != 0:
                    return False

        except Exception as _:
            return False

        return True

    def _unswap(self) -> bool:
        if TEST_MODE:
            return True
        self._queued_command.disk.update_mountpoints()
        mountpoints = self._queued_command.disk.get_mountpoints_map()
        unswap_them = []
        oh_no = None
        for part in mountpoints:
            if mountpoints[part] == "[SWAP]":
                unswap_them.append(part)
            else:
                oh_no = part
                break
        if oh_no:
            self._queued_command.notify_finish_with_error(f"Partition {oh_no} is mounted as {mountpoints[oh_no]}")
            return False
        if len(unswap_them) > 0:
            self._queued_command.notify_start("Unswapping the disk")
            for path in unswap_them:
                sp = subprocess.Popen(("sudo", "swapoff", path))
                exitcode = sp.wait()
                if exitcode != 0:
                    self._queued_command.notify_finish_with_error(f"Failed to unswap {path}, exit code {str(exitcode)}")
                    return False
            self._queued_command.disk.update_mountpoints()
        return True

    def sleep(self, _cmd: str, dev: str):
        self._queued_command.notify_start("Calling hdparm")
        exitcode = self._call_hdparm_for_sleep(dev)
        if exitcode == 0:
            self._queued_command.notify_finish("Good night!")
        else:
            self._queued_command.notify_finish_with_error(f"hdparm exited with status {str(exitcode)}")

    def sudo_password(self, _cmd: str, password: str):
        global needs_sudo
        with clients_lock:
            if not needs_sudo:
                return

            result = subprocess.run(
                ["sudo", "-vS"],
                input=password + "\n",
                encoding="utf-8",
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            # output, stderr = pipe.communicate(password.encode() + b"\n")
            # exitcode = pipe.wait()

            if result.returncode == 0:
                needs_sudo = False
                SudoSessionKeeper().start()
            else:
                self.send_msg("sudo_password")

    def _call_hdparm_for_sleep(self, dev: str):
        return self._call_shell_command(("sudo", "hdparm", "-Y", dev))

    def get_smartctl(self, cmd: str, args: str):
        params = self._get_smartctl(args, False)
        if params:
            self.send_msg(cmd, params)

    def queued_get_smartctl(self, cmd: str, args: str):
        self._get_smartctl(args, True)
        # if params:
        #     self.send_msg(cmd, params)

    def _get_smartctl(self, dev: str, queued: bool):
        if queued:
            self._queued_command.notify_start("Getting smarter")

        pipe = subprocess.Popen(
            ("sudo", "-n", "smartctl", "-j", "-a", dev),
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        output = pipe.stdout.read().decode("utf-8")
        stderr = pipe.stderr.read().decode("utf-8")
        exitcode = pipe.wait()

        if exitcode == 0:
            smartctl_returned_valid = True
        else:
            exitcode_bytes = exitcode.to_bytes(8, "little")
            if exitcode_bytes[0] == 1 or exitcode_bytes[1] == 1 or exitcode_bytes[2] == 1:
                smartctl_returned_valid = False
            else:
                # TODO: parse remaining bits (https://github.com/WEEE-Open/pesto/issues/71)
                smartctl_returned_valid = True

        updated = False
        status = None

        if smartctl_returned_valid:
            status = get_smartctl_status(output)
            if queued:
                if not status:
                    self._queued_command.notify_error("Error while parsing smartctl status")
                    return {
                        "disk": dev,
                        "status": status,
                        "updated": updated,
                        "exitcode": exitcode,
                        "output": output,
                        "stderr": stderr,
                    }
        else:
            if queued:
                self._queued_command.notify_error("smartctl failed")
            return {
                "disk": dev,
                "status": status,
                "updated": updated,
                "exitcode": exitcode,
                "output": output,
                "stderr": stderr,
            }

        if queued and status:
            self._queued_command.notify_percentage(50.0, "Updating tarallo if needed")

            with disks_lock:
                update_disks_if_needed(self)
                disk_ref = disks[dev]

            # noinspection PyBroadException
            try:
                updated = disk_ref.update_status(status)
            except Exception as e:
                self._queued_command.notify_error("Error during upload")
                logging.warning(
                    f"[{self._the_id}] Can't update status of {dev} on tarallo",
                    exc_info=e,
                )
            self._queued_command.notify_finish(f"Disk is {status}")
        return {
            "disk": dev,
            "status": status,
            "updated": updated,
            "exitcode": exitcode,
            "output": output,
            "stderr": stderr,
        }

    # noinspection PyUnusedLocal
    def queued_upload_to_tarallo(self, cmd: str, args: str):
        self._upload_to_tarallo(args, True)

    # noinspection PyUnusedLocal
    def upload_to_tarallo(self, cmd: str, args: str):
        self._upload_to_tarallo(args, False)

    def _upload_to_tarallo(self, dev: str, queued: bool):
        list_dev = dev.split(" ")
        dev = list_dev[0]
        loc = list_dev[1]
        if TEST_MODE:
            self._queued_command.notify_finish("This doesn't do anything when test mode is enabled")
            return

        if queued:
            self._queued_command.notify_start("Preparing to upload")

        # return {
        #     "disk": dev,
        #     "status": status,
        #     "updated": updated,
        #     "exitcode": exitcode,
        #     "output": output,
        #     "stderr": stderr,
        # }
        smartctl = self._get_smartctl(dev, False)

        if queued:
            self._queued_command.notify_percentage(50.0, "smartctl output obtained")

        if queued and not smartctl.get("output"):
            self._queued_command.notify_finish_with_error("Could not get smartctl output")
            return

        if queued and not smartctl.get("status"):
            self._queued_command.notify_error("Could not determine disk status")

        features = parse_single_disk(json.loads(smartctl.get("output", "")))

        if queued:
            self._queued_command.notify_percentage(75.0, "Parsing done")

        with disks_lock:
            # update_disks_if_needed(self)
            disk_ref = disks[dev]

        try:
            code = disk_ref.create_on_tarallo(features, loc)
        except ValidationError as e:
            if queued:
                self.send_msg(
                    "error_that_can_be_manually_fixed",
                    {"message": "Upload failed due to validation error: " + str(e), "disk": dev},
                )
                self._queued_command.notify_finish_with_error("Upload failed due to validation error: " + str(e))
            return
        except NotAuthorizedError as e:
            if queued:
                self.send_msg(
                    "error_that_can_be_manually_fixed",
                    {"message": "Upload failed due to authorization error: " + str(e), "disk": dev},
                )
                self._queued_command.notify_finish_with_error("Upload failed due to authorization error: " + str(e))
            return

        with disks_lock:
            if code:
                disk_ref.set_code(code)

            try:
                disk_ref.update_from_tarallo_if_needed()
            except ErrorThatCanBeManuallyFixed as e:
                if queued:
                    self.send_msg(
                        "error_that_can_be_manually_fixed",
                        {"message": str(e), "disk": dev},
                    )
                    self._queued_command.notify_finish_with_error("Upload succeeded, but an error was reported")
                return

        logging.info(f"[{self._the_id}] created {disk_ref.get_path()} on tarallo as {code if code else 'unknown code'}")
        if queued:
            self._queued_command.notify_finish("Upload done")

    @staticmethod
    def _encode_param(param):
        return json.dumps(param, separators=(",", ":"), indent=None)

    def send_msg(self, cmd: str, param=None, the_id: Optional[int] = None):
        logging.debug(f"[{self._the_id}] Sending {cmd}{ ' with args' if param else ''} to client")
        the_id = the_id or self._the_id
        thread = clients.get(the_id)
        if thread is None:
            logging.info(f"[{the_id}] Connection already closed while trying to send {cmd}")
        else:
            thread: TurboProtocol
            # noinspection PyBroadException
            try:
                if param is None:
                    response_string = cmd
                else:
                    j_param = self._encode_param(param)
                    response_string = f"{cmd} {j_param}"
                # It's there but pycharm doesn't believe it
                # noinspection PyUnresolvedReferences
                reactor.callFromThread(TurboProtocol.send_msg, thread, response_string)
            except Exception:
                logging.warning(f"[{the_id}] Something blew up while trying to send {cmd} (connection already closed?)")

    def get_disks(self, cmd: str, _nothing: str):
        result = []
        with disks_lock:
            # Sent regardless
            update_disks_if_needed(self, False)
            for disk in disks:
                result.append(disks[disk].serialize_disk())
        self.send_msg(cmd, result)

    @staticmethod
    def _pretty_print_iso(iso: str):
        filename = iso.rsplit("/", 1)[-1]
        filename = filename.split(".", 1)[0]
        filename = filename.replace("-", " ").replace("_", " ")
        return filename

    def dd(self, inputf: str, outputf: str, bs: int = 4096, output_delay: float = 1.0):
        if os.path.exists(inputf):
            try:
                with open(inputf, "rb") as fin:
                    print("Input file opened successfully!")
                    with open(outputf, "wb") as fout:
                        print("Output file opened successfully!")
                        s = os.stat(inputf).st_mode
                        is_special = stat.S_ISBLK(s) or stat.S_ISCHR(s)
                        total_size = get_block_size(outputf) if is_special else os.path.getsize(inputf)
                        completed_size = 0
                        elapsed_time = 0
                        actual_time = time.time()
                        while True:
                            if fout.write(fin.read(bs)) == 0:
                                break
                            completed_size += bs
                            if elapsed_time > output_delay:
                                percentage = (completed_size / total_size) * 100
                                self._queued_command.notify_percentage(percentage)
                                elapsed_time = 0
                            else:
                                elapsed_time += time.time() - actual_time
                                actual_time = time.time()
                        return True
            except KeyboardInterrupt:
                print("\nInterrupted!")
                os.system("sync")
                return False
        else:
            return False

    def stop_process(self, cmd: str, args: str):
        logging.debug(f"Received stop request for {args}")
        thread = find_thread_from_pid(args)
        thread.stop_asap()

    def _call_shell_command(self, command: tuple):
        if TEST_MODE:
            logging.debug(f"Simulating command: {' '.join(command)}")
            return 0
        logging.debug(f"[{self._the_id}] Running command {' '.join(command)}")

        try:
            res = subprocess.Popen(
                command,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
        except FileNotFoundError as _:
            return sys.maxsize

        exitcode = res.wait()
        if exitcode != 0:
            logging.warning(f"[{self._the_id}] Command '{' '.join(command)}' returned {str(exitcode)}")
        return exitcode


class QueuedCommand:
    def __init__(self, disk: Disk, command_runner: CommandRunner):
        self.disk = disk
        self._target = self.disk.get_path()
        self.command_runner = command_runner
        self._percentage = 0.0
        self._started = False
        self._finished = False
        self._error = False
        self._stopped = False
        self._stale = False
        self._notifications_lock = threading.Lock()
        self._text = "Queued"
        self._to_delete = False
        self._deleted = False
        date = datetime.today().strftime("%Y%m%d%H%M")
        with queued_commands_lock:
            self._id = f"{date}-{str(len(queued_commands))}"
            queued_commands.append(self)
        with self._notifications_lock:
            self.send_to_all_clients()

    def id_is(self, the_id: str):
        return self._id == the_id

    def id(self):
        return self._id

    def lock_notifications(self):
        self._notifications_lock.acquire()

    def unlock_notifications(self):
        self._notifications_lock.release()

    def notify_start(self, text: Optional[str] = None):
        with self._notifications_lock:
            if text is not None:
                self._text = text
            self._started = True
            self._percentage = 0.0
            self.send_to_all_clients()

    def notify_finish_safe(self, text: Optional[str] = None):
        with self._notifications_lock:
            if self._finished:
                return
        # TODO: RLock? Probably not needed
        self.notify_finish(text)

    def notify_finish(self, text: Optional[str] = None):
        with self._notifications_lock:
            if text is not None:
                self._text = text
            self._finished = True
            self._percentage = 100.0
            self.send_to_all_clients()

            if self._to_delete:
                self.notify_delete()

    def notify_finish_with_error(self, text: Optional[str] = None):
        with self._notifications_lock:
            if text is not None:
                self._text = text
            self._finished = True
            self._error = True
            self._percentage = 100.0
            self.send_to_all_clients()

            if self._to_delete:
                self.notify_delete()

    def notify_error(self, text: Optional[str] = None):
        with self._notifications_lock:
            if text is not None:
                self._text = text
            self._error = True
            self.send_to_all_clients()

    def notify_stopped(self, text: Optional[str] = None):
        with self._notifications_lock:
            if text is not None:
                self._text = text
            self._stopped = True
            self.send_to_all_clients()

    def notify_percentage(self, percent: float, text: Optional[str] = None):
        with self._notifications_lock:
            if text is not None:
                self._text = text
            self._percentage = percent
            self.send_to_all_clients()

    def delete_when_done(self):
        self._to_delete = True
        # Locking is pointless, notify_delete must be called after releasing the lock anyway
        if self._finished:
            self.notify_delete()

    def notify_delete(self):
        if self._deleted:
            return

        with self._notifications_lock:
            with queued_commands_lock:
                try:
                    queued_commands.remove(self)
                    self._deleted = True
                except ValueError:
                    # Already deleted, do not send anything
                    pass
                # If already deleted, this will do nothing
                self.disk.dequeue(self)
            if self._deleted:
                self.delete_from_all_clients()

    def send_to_all_clients(self):
        # For added safety, do not send updates of deleted rows (the reference may still exist)
        if self._deleted:
            return

        param = self.serialize_me()
        # logging.debug(f"[ALL] Sending queue update for {self.command_runner.get_cmd()}")
        for client in clients:
            # send_msg calls reactor.callFromThread and reactor is single threaded, so no risk here
            # send_all is always called with a lock, so all status updates are sent in the expected order
            self.command_runner.send_msg("queue_status", param, client)

    def delete_from_all_clients(self):
        param = {
            "id": self._id,
        }
        for client in clients:
            self.command_runner.send_msg("remove", param, client)

    def serialize_me(self) -> dict:
        return {
            "id": self._id,
            "command": self.command_runner.get_cmd(),
            "text": self._text,
            "target": self._target,
            "percentage": self._percentage,
            "started": self._started,
            "finished": self._finished,
            "error": self._error,
            "stale": self._stale,
            "stopped": self._stopped,
        }


class TurboProtocol(LineOnlyReceiver):
    def __init__(self):
        global needs_sudo
        self._id = -1
        self.delimiter = b"\n"
        self._delimiter_found = False
        needs_sudo = self.sudo_needs_password()

    def connectionMade(self):
        self._id = self.factory.conn_id
        self.factory.conn_id += 1
        with clients_lock:
            clients[self._id] = self
        logging.debug(f"[{str(self._id)}] Client connected")

    def connectionLost(self, reason=protocol.connectionDone):
        logging.debug(f"[{str(self._id)}] Client disconnected")
        with clients_lock:
            del clients[self._id]

    def lineReceived(self, line):
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError as e:
            logging.warning(f"[{str(self._id)}] Oh no, UnicodeDecodeError!", exc_info=e)
            return

        # \n is stripped by twisted, but with \r\n the \r is still there
        if not self._delimiter_found:
            if len(line) > 0 and line[-1] == "\r":
                self.delimiter = b"\r\n"
                logging.debug(f"[{str(self._id)}] Client has delimiter \\r\\n")
            else:
                logging.debug(f"[{str(self._id)}] Client has delimiter \\n")
            self._delimiter_found = True

            global needs_sudo
            if needs_sudo:
                self.send_msg("sudo_password")

        # Strip \r on first message (if \r\n) and any trailing whitespace
        line = line.strip()
        if line.startswith("exit"):
            logging.debug(f"[{str(self._id)}] Client sent exit, closing connection")
            self.transport.loseConnection()
        else:
            parts = line.split(" ", 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            # Create the thread. It will enqueue and/or start itself.
            CommandRunner(cmd, args, self._id)

    def send_msg(self, response: str):
        if self._delimiter_found:
            self.sendLine(response.encode("utf-8"))
        else:
            logging.warning(f"[{str(self._id)}] Cannot send command to client due to unknown delimiter: {response}")

    def sudo_needs_password(self):
        exitcode = subprocess.run(["sudo", "-nv"])
        return exitcode.returncode != 0


def update_disks_if_needed(this_thread: Optional[CommandRunner], send: bool = True):  # , disk: Optional[str] = None):
    with disks_lock:
        disks_lsblk = get_disks()
        found_disks = set()

        changes = False
        for lsblk in disks_lsblk:
            path = lsblk.get("path")
            if path:
                path = str(lsblk["path"])
            else:
                # logging.warning("Disk has no path, ignoring: " + lsblk)
                continue

            found_disks.add(path)
            add = False
            if path in disks:
                if disks[path].compare_composite_id(lsblk):
                    try:
                        more_changes = disks[path].update_from_tarallo_if_needed()
                        changes = changes or more_changes
                    except ErrorThatCanBeManuallyFixed as e:
                        if this_thread:
                            this_thread.send_msg(
                                "error_that_can_be_manually_fixed",
                                {"message": str(e), "disk": path},
                            )

                else:
                    logging.info(f"Disk {path} has changed")
                    del disks[path]
                    add = True
            else:
                logging.info(f"Disk {path} is new")
                add = True
            if add:
                # noinspection PyBroadException
                try:
                    global TARALLO
                    disks[path] = Disk(lsblk, TARALLO)
                    changes = True
                except Exception as e:
                    logging.warning("Exception while re-scanning for disks, skipping", exc_info=e)

        # RuntimeError: dictionary changed size during iteration
        to_delete = []
        for path in disks:
            if path in found_disks:
                continue
            else:
                logging.info(f"Disk {path} is gone")
                to_delete.append(path)

        for path in to_delete:
            del disks[path]
            changes = True

        if send and changes and this_thread:
            result = []
            with disks_lock:
                for disk in disks:
                    result.append(disks[disk].serialize_disk())
            this_thread.send_msg("get_disks", result)


def scan_for_disks():
    with disks_lock:
        logging.debug("Scanning for disks")
        disks_lsblk = get_disks()
        for disk_lsblk in disks_lsblk:
            path = disk_lsblk.get("path")
            if path:
                path = str(disk_lsblk["path"])
            else:
                logging.warning("Disk has no path, ignoring: " + disk_lsblk)
                continue
            # noinspection PyBroadException
            try:
                global TARALLO
                disks[path] = Disk(disk_lsblk, TARALLO)
            except Exception as e:
                logging.warning("Exception while scanning for disks, skipping", exc_info=e)


def get_disks(path: Optional[str] = None):
    disks_lsblk = get_disks_linux(path)
    return disks_lsblk


def find_thread_from_pid(pinolo_pid: str) -> CommandRunner:
    for thread in threading.enumerate():
        if isinstance(thread, CommandRunner):
            command = thread.get_queued_command()
            if command is None:
                continue
            if command.id() == pinolo_pid:
                return thread


def main():
    scan_for_disks()
    ip = os.getenv("IP")
    port = os.getenv("PORT")
    global TEST_MODE
    TEST_MODE = bool(int(os.getenv("TEST_MODE", False)))

    if TEST_MODE:
        logging.warning("Test mode is enabled, no destructive actions will be performed")
    else:
        logging.debug("TEST MODE IS DISABLED! Do you really want to risk your hard drive?")

    try:
        factory = protocol.ServerFactory()
        factory.protocol = TurboProtocol
        factory.conn_id = 0

        logging.info(f"Listening on {ip} port {port}")

        # noinspection PyUnresolvedReferences
        reactor.listenTCP(int(port), factory, interface=ip)

        # noinspection PyUnresolvedReferences
        reactor.run()
    except KeyboardInterrupt:
        print("KeyboardInterrupt, terminating")
    finally:
        # TODO: reactor has already stopped here, but threads may send messages... what happens? A big crash, right?
        while len(running_commands) > 0:
            with running_commands_lock:
                thread_to_stop = next(iter(running_commands))
            thread_to_stop: CommandRunner
            thread_to_stop.stop_asap()
            thread_to_stop.join()


def load_settings():
    # Load in order each file if exists, variables are not overwritten
    here = os.path.dirname(os.path.realpath(__file__))
    load_dotenv(here + "/.env")
    load_dotenv(f"~/.conf/WEEE-Open/{NAME}.conf")
    load_dotenv(f"/etc/{NAME}.conf")
    # Defaults
    config = StringIO("IP=0.0.0.0\nPORT=1030\nLOGLEVEL=INFO")
    load_dotenv(stream=config)

    logging.basicConfig(format="%(message)s", level=getattr(logging, os.getenv("LOGLEVEL").upper()))

    if os.getenv("CLOSE_AT_END_TIMER") is not None:
        global CLOSE_AT_END_TIMER
        CLOSE_AT_END_TIMER = int(os.getenv("CLOSE_AT_END_TIMER"))

    url = os.getenv("TARALLO_URL") or logging.warning("TARALLO_URL is not set, tarallo will be unavailable")
    token = os.getenv("TARALLO_TOKEN") or logging.warning("TARALLO_TOKEN is not set, tarallo will be unavailable")

    if url and token:
        global TARALLO
        TARALLO = Tarallo.Tarallo(url, token)


def get_smartctl_status(smartctl_output: str) -> Optional[str]:
    # noinspection PyBroadException
    try:
        smartctl = json.loads(smartctl_output)
        smart, failing_now = extract_smart_data(smartctl)
        status = smart_health_status(smart, failing_now)
        return status
    except Exception as e:
        logging.error("Failed to parse smartctl output", exc_info=e)
        return None


def find_mounts(el: dict):
    mounts = {}
    if el["mountpoint"] is not None:
        mounts[el["path"]] = el["mountpoint"]
    if "children" in el:
        children = el["children"]
        for child in children:
            children_mounts = find_mounts(child)
            mounts = {**mounts, **children_mounts}
    return mounts


def get_disks_linux(path: Optional[str] = None) -> list:
    # Name is required, otherwise the tree is flattened
    # To filter out loop devices, ODDs, tape drives and network devices: --exclude 7,9,11,43
    # See: https://www.kernel.org/doc/Documentation/admin-guide/devices.txt
    # Also: https://unix.stackexchange.com/a/610634
    output = subprocess.getoutput(f"lsblk --exclude 7,9,11,43 -b -o NAME,PATH,VENDOR,MODEL,SERIAL,HOTPLUG,ROTA,MOUNTPOINT,SIZE -J {path if path else ''}")
    jsonized = json.loads(output)
    if "blockdevices" in jsonized:
        result = jsonized["blockdevices"]
    else:
        result = []
    for el in result:
        # Skip empty disks (empty SD card reader)
        if el["size"] == 0:
            continue

        mounts = find_mounts(el)
        if "children" in el:
            del el["children"]
        if "name" in el:
            del el["name"]
        # List of partition names (/dev/sda1) to filesystem directories
        el["mountpoint_map"] = mounts
        # List of filesystem directories
        el["mountpoint"] = list(mounts.values())

    return result


def try_stop_at_end():
    logging.debug(time.time())
    if CLOSE_AT_END:
        with clients_lock:
            if len(clients) <= 0:
                with queued_commands_lock:
                    with running_commands_lock:
                        if len(running_commands) <= 0:
                            empty = True
                            for path in disks:
                                empty = disks[path].queue_is_empty()
                                if not empty:
                                    break
                            if empty:
                                logging.debug("CLOSE_AT_END met all the conditions, stopping reactor")
                                # noinspection PyUnresolvedReferences
                                reactor.stop()
        # noinspection PyUnresolvedReferences
        reactor.callLater(CLOSE_AT_END_TIMER, try_stop_at_end)


def get_block_size(path):
    """Return device size in bytes."""
    with open(path, "rb") as f:
        return f.seek(0, 2) or f.tell()


def run_command_on_partition(dev: str, cmd: str) -> bool:
    s = os.stat(dev).st_mode
    if stat.S_ISBLK(s):
        res = os.system(cmd)
        if res == 0:
            return True
    return False


def user_groups_checks():
    try:
        res = subprocess.getoutput("groups $USER")
    except FileNotFoundError as _:
        logging.error("Unknown subprocess error in init_checks()")
        return
    warn = False
    if ":" in res:
        if "disk" not in res.split(":")[1]:
            warn = True
    else:
        if "disk" not in res.split(" "):
            warn = True
    if warn:
        user = os.getenv("USER")
        logging.warning(
            f"User {user} on the server is not in disk group and it may not have sufficient permissions to use smartctl.\n"
            f"You can add it in with the command\n\n"
            f"\tsudo usermod -a -G disk $USER\n\n"
            f"and restarting the user session (logout and login)."
        )


TARALLO = None
CLOSE_AT_END = False
CLOSE_AT_END_LOCK = threading.Lock()
CLOSE_AT_END_TIMER = 5

needs_sudo = False

clients: Dict[int, TurboProtocol] = {}
clients_lock = threading.Lock()

disks: Dict[str, Disk] = {}
disks_lock = threading.RLock()

running_commands: Set[CommandRunner] = set()
running_commands_lock = threading.Lock()

queued_commands: List[QueuedCommand] = []
queued_commands_lock = threading.Lock()


if __name__ == "__main__":
    user_groups_checks()
    load_settings()
    if bool(os.getenv("DAEMONIZE", False)):
        import daemon
        from daemon import pidfile

        out = open("/opt/pesto/stdout.log", "w+")
        err = open("/opt/pesto/stderr.log", "w+")

        pid = pidfile.PIDLockFile(os.getenv("LOCKFILE_PATH", f"/home/pesto/{NAME}.pid"))
        context = daemon.DaemonContext(pidfile=pid, stdout=out, stderr=err)

        with context:
            main()
    else:
        main()
