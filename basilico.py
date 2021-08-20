#!/usr/bin/env python
import json
import subprocess
import sys
import os
from collections import deque
from typing import Optional, Callable, Any
from pytarallo import Tarallo
from dotenv import load_dotenv
from io import StringIO
from twisted.internet import reactor, protocol
from twisted.protocols.basic import LineOnlyReceiver
import threading
import logging
from datetime import datetime

from utilites import smartctl_get_status, parse_smartctl_output

NAME = "basilico"
# Use env vars, do not change the value here
TEST_MODE = False
CURRENT_OS = sys.platform


class Disk:
    def __init__(self, lsblk, tarallo: Optional[Tarallo.Tarallo]):
        self._lsblk = lsblk
        if "path" not in self._lsblk:
            raise RuntimeError("lsblk did not provide path for this disk: " + self._lsblk)
        self._path = str(self._lsblk["path"])
        self._code = None
        self._item = None

        self._queue_lock = threading.Lock()
        self._commands_queue = deque()

        self._tarallo = tarallo
        self._get_code(False)
        self._get_item()

    def enqueue(self, cmd_runner):
        cmd_runner: CommandRunner
        with self._queue_lock:
            self._commands_queue.append(cmd_runner)
            if len(self._commands_queue) == 1:
                cmd_runner.start()

    def dequeue(self, cmd_runner):
        cmd_runner: CommandRunner
        with self._queue_lock:
            self._commands_queue.remove(cmd_runner)
            if len(self._commands_queue) > 0:
                next_in_line: CommandRunner = self._commands_queue[0]
                if not next_in_line.is_alive():
                    next_in_line.start()

    def get_path(self):
        return self._path

    def update_from_tarallo_if_needed(self):
        if not self._code:
            self._get_code(True)
        self._get_item()

    def serialize_disk(self):
        result = self._lsblk
        result["code"] = self._code
        return result

    def update_status(self, status: str) -> bool:
        if self._tarallo and self._code:
            self._tarallo.update_item_features(self._code, {"smart-data": status})
            return True
        return False

    def _get_code(self, stop_on_error: bool = True):
        if not self._tarallo:
            self._code = None
            return
        if "serial" not in self._lsblk:
            self._code = None
            if stop_on_error:
                raise ErrorThatCanBeManuallyFixed(f"Disk {self._path} has no serial number")

        sn = self._lsblk["serial"]
        sn: str
        if sn.startswith('WD-'):
            sn = sn[3:]

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

    def _get_item(self):
        if self._tarallo and self._code:
            self._item = self._tarallo.get_item(self._code, 0)
        else:
            self._item = None


class ErrorThatCanBeManuallyFixed(BaseException):
    pass


class CommandRunner(threading.Thread):
    def __init__(self, cmd: str, args: str, the_id: int):
        threading.Thread.__init__(self)
        self._cmd = cmd
        self._args = args
        self._the_id = the_id
        self._go = True

        self._function, disk_for_queue = self.dispatch_command(cmd, args)
        if not self._function:
            self.send_msg("error", {"message": "Unrecognized command", "command": cmd})
            self._function = None
        self._queued_command = None
        if disk_for_queue:
            # No need to lock, disks are never deleted, so if it is found then it is valid
            disk = disks.get(disk_for_queue, None)
            if not disk:
                self.send_msg('error', {"message": f"{args} is not a disk"})
                self._function = None
            # Do not start yet, just prepare the data structure
            self._queued_command = QueuedCommand(disk, self)

            # And enqueue, which will start it when needed
            with queued_commands_lock:
                disk.enqueue(self)
        else:
            # Start immediately
            self.start()

    def get_cmd(self):
        return self._cmd

    def run(self):
        try:
            # Stop immediately if nothing was dispatched
            if not self._function:
                return
            # Also stop if program is terminating
            if not self._go:
                return

            # Otherwise, lessss goooooo!
            with running_commands_lock:
                running_commands.add(self)

            try:
                self._function(self._cmd, self._args)
            except BaseException as e:
                logging.error(f"[{self._the_id}] BIG ERROR in command thread", exc_info=e)
        finally:
            # The next thread on the disk can start, if there's a queue
            if self._queued_command:
                # TODO: this will notify finish twice. But it could be checked that the update is actually an update.
                self._queued_command.notify_finish()
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
            "smartctl": self.get_smartctl,
            "queued_smartctl": self.queued_get_smartctl,
            "queued_badblocks": self.badblocks,
            "queued_cannolo": self.cannolo,
            "get_disks": self.get_disks,
            "ping": self.ping,
            "get_queue": self.get_queue,
        }
        logging.debug(f"[{self._the_id}] Received command {cmd}{' with args' if len(args) > 0 else ''}")
        if cmd.startswith('queued_'):
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
        return args

    # noinspection PyUnusedLocal
    def badblocks(self, cmd: str, dev: str):
        self._queued_command.notify_start("Running")
        # if not TEST_MODE:
        # TODO: code from turbofresa goes here
        self._queued_command.notify_percentage(10, "0 bad blocks")
        threading.Event().wait(2)
        self._queued_command.notify_percentage(20, "0 bad blocks")
        threading.Event().wait(2)
        self._queued_command.notify_percentage(30, "2 bad blocks")
        threading.Event().wait(2)
        self._queued_command.notify_percentage(42, "2 bad blocks")
        threading.Event().wait(2)
        self._queued_command.notify_percentage(60, "2 bad blocks")
        threading.Event().wait(2)
        self._queued_command.notify_percentage(80, "2 bad blocks")
        threading.Event().wait(2)
        self._queued_command.notify_percentage(99, "3 bad blocks")
        threading.Event().wait(2)
        self._queued_command.notify_finish("3 bad blocks")

    # noinspection PyUnusedLocal
    def ping(self, cmd: str, dev: str):
        self.send_msg("pong", None)

    # noinspection PyUnusedLocal
    def cannolo(self, cmd: str, dev: str):
        self._queued_command.notify_start("Cannoling")
        # if not TEST_MODE:
        # TODO: code from turbofresa goes here
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
        self._queued_command.notify_finish("Xubuntu 99.99 LTS installed!")

    def get_smartctl(self, cmd: str, args: str):
        params = self._get_smartctl(args, False)
        if params:
            self.send_msg(cmd, params)

    def queued_get_smartctl(self, cmd: str, args: str):
        params = self._get_smartctl(args, True)
        if params:
            self.send_msg(cmd, params)

    def _get_smartctl(self, dev: str, queued: bool):
        if queued:
            self._queued_command.notify_start("Getting smarter")
        if CURRENT_OS == 'win32':
            pipe = subprocess \
                .Popen(("smartctl", "-a", f"/dev/pd{dev}"), shell=True, stderr=subprocess.PIPE,
                       stdout=subprocess.PIPE)
            output = pipe.stdout.read().decode('utf-8')
            stderr = pipe.stderr.read().decode('utf-16')
        else:
            pipe = subprocess \
                .Popen(("sudo", "smartctl", "-a", dev), stderr=subprocess.PIPE,
                       stdout=subprocess.PIPE)
            output = pipe.stdout.read().decode('utf-8')
            stderr = pipe.stderr.read().decode('utf-8')
        exitcode = pipe.wait()

        updated = False
        status = None

        if exitcode == 0 or (CURRENT_OS == 'win32' and exitcode == 4):
            status = get_smartctl_status(output)
            if queued:
                if not status:
                    self._queued_command.notify_error("Error while parsing smartctl status")
                    return
        else:
            if queued:
                self._queued_command.notify_error("smartctl failed")
                return

        if queued and status:
            self._queued_command.notify_percentage(50.0, "Updating tarallo if needed")
            with disks_lock:
                self.update_disk_if_needed(disks[dev])
                # noinspection PyBroadException
                try:
                    updated = disks[dev].update_status(status)
                except BaseException as e:
                    self._queued_command.notify_error("Error during upload")
                    logging.warning(f"[{self._the_id}] Can't update status of {dev} on tarallo", exc_info=e)
        return {
            "disk": dev,
            "status": status,
            "updated": updated,
            "exitcode": exitcode,
            "output": output,
            "stderr": stderr,
        }

    def update_disk_if_needed(self, disk: Disk):
        # TODO: a more granular lock is possible, here. But is it really needed?
        # Do not use the queue lock, though
        with disks_lock:
            # noinspection PyBroadException
            try:
                disk.update_from_tarallo_if_needed()
            except ErrorThatCanBeManuallyFixed as e:
                self.send_msg("error_that_can_be_manually_fixed", {"message": str(e), "disk": disk})
            except BaseException:
                pass

    @staticmethod
    def _encode_param(param):
        return json.dumps(param, separators=(',', ':'), indent=None)

    def send_msg(self, cmd: str, param=None, the_id: Optional[int] = None):
        logging.debug(f"[{self._the_id}] Sending {cmd}{ ' with args' if param else ''} to client")
        the_id = the_id or self._the_id
        thread = clients.get(the_id)
        if thread is None:
            logging\
                .info(f"[{the_id}] Connection already closed while trying to send {cmd}")
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
            except BaseException:
                logging\
                    .warning(f"[{the_id}] Something blew up while trying to send {cmd} (connection already closed?)")

    def get_disks(self, cmd: str, dev: str):
        if CURRENT_OS == 'win32':
            param = get_disks_win()
        else:
            param = self.get_disks_to_send()
        self.send_msg(cmd, param)

    def get_disks_to_send(self):
        result = []
        with disks_lock:
            for disk in disks:
                if disks[disk] is None:
                    lsblk = get_disks(disk)
                    if len(lsblk) > 0:
                        lsblk = lsblk[0]
                    # noinspection PyBroadException
                    try:
                        disks[disk] = Disk(lsblk, TARALLO)
                    except BaseException as e:
                        logging.warning(f"Error with disk {disk} still remains", exc_info=e)
                if disks[disk] is not None:
                    self.update_disk_if_needed(disks[disk])
                    result.append(disks[disk].serialize_disk())
        return result


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
        date = datetime.today().strftime('%Y%m%d%H%M')
        with queued_commands_lock:
            self._id = f"{date}-{str(len(queued_commands))}"
            queued_commands.append(self)
        with self._notifications_lock:
            self.send_to_all_clients()

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

    def notify_finish(self, text: Optional[str] = None):
        with self._notifications_lock:
            if text is not None:
                self._text = text
            self._finished = True
            self._percentage = 100.0
            self.send_to_all_clients()

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

    def send_to_all_clients(self):
        param = self.serialize_me()
        # logging.debug(f"[ALL] Sending queue update for {self.command_runner.get_cmd()}")
        for client in clients:
            # send_msg calls reactor.callFromThread and reactor is single threaded, so no risk here
            # send_all is always called with a lock, so all status updates are sent in the expected order
            self.command_runner.send_msg("queue_status", param, client)

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
        self._id = -1
        self.delimiter = b'\n'
        self._delimiter_found = False

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
            line = line.decode('utf-8')
        except UnicodeDecodeError as e:
            logging.warning(f"[{str(self._id)}] Oh no, UnicodeDecodeError!", exc_info=e)
            return

        # \n is stripped by twisted, but with \r\n the \r is still there
        if not self._delimiter_found:
            if len(line) > 0 and line[-1] == '\r':
                self.delimiter = b'\r\n'
                logging.debug(f"[{str(self._id)}] Client has delimiter \\r\\n")
            else:
                logging.debug(f"[{str(self._id)}] Client has delimiter \\n")
            self._delimiter_found = True

        # Strip \r on first message (if \r\n) and any trailing whitespace
        line = line.strip()
        if line.startswith('exit'):
            logging.debug(f"[{str(self._id)}] Client sent exit, closing connection")
            self.transport.loseConnection()
        else:
            parts = line.split(' ', 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ''

            # Create the thread. It will enqueue and/or start itself.
            CommandRunner(cmd, args, self._id)

    def send_msg(self, response: str):
        if self._delimiter_found:
            self.sendLine(response.encode('utf-8'))
        else:
            logging\
                .warning(f"[{str(self._id)}] Cannot send command to client due to unknown delimiter: {response}")


def scan_for_disks():
    logging.debug("Scanning for disks")
    if CURRENT_OS == 'win32':
        disks_lsblk = get_disks_win()
    else:
        disks_lsblk = get_disks()
    for disk in disks_lsblk:
        if "path" not in disk:
            logging.warning("Disk has no path, ignoring: " + disk)
            continue
        path = str(disk["path"])
        # noinspection PyBroadException
        try:
            with disks_lock:
                disks[path] = Disk(disk, TARALLO)
        except BaseException as e:
            logging.warning("Exception while scanning disk, skipping", exc_info=e)


def main():
    scan_for_disks()
    ip = os.getenv("IP")
    port = os.getenv("PORT")
    global TEST_MODE
    TEST_MODE = bool(os.getenv("TEST_MODE", False))

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
    load_dotenv(here + '/.env')
    load_dotenv(f'~/.conf/WEEE-Open/{NAME}.conf')
    load_dotenv(f'/etc/{NAME}.conf')
    # Defaults
    config = StringIO("IP=127.0.0.1\nPORT=1030\nLOGLEVEL=INFO")
    load_dotenv(stream=config)

    logging.basicConfig(format='%(message)s', level=getattr(logging, os.getenv("LOGLEVEL").upper()))

    url = os.getenv('TARALLO_URL') or logging.warning('TARALLO_URL is not set, tarallo will be unavailable')
    token = os.getenv('TARALLO_TOKEN') or logging.warning('TARALLO_TOKEN is not set, tarallo will be unavailable')

    if url and token:
        global TARALLO
        TARALLO = Tarallo.Tarallo(url, token)


def get_disks_win() -> list:
    the_map = {
        "DiskNumber": "path",
        "Model": "model",
        "SerialNumber": "serial",
        "Size": "size",
        # "": "hotplug",
        # "": "rota",
        # "IsBoot": "boot",
    }

    pipe = subprocess.Popen(["powershell", "Get-Disk", "|", "ConvertTo-Json"], stdout=subprocess.PIPE)
    output = pipe.stdout.read().decode('utf-8')
    output = json.loads(output)
    pipe.kill()
    big_result = []

    # If there's a single disk, Windows returns the disk dict directly, instead
    # of a list with a single element
    if "DiskNumber" in output:
        output = [output]
    for disk in output:
        disk: dict
        if disk["OperationalStatus"] == "No Media":
            continue
        result = {}
        for k in the_map:
            result[the_map[k]] = str(disk[k]).strip()

        if "serial" in result:
            if result["serial"].startswith("WD-"):
                result["serial"] = result["serial"][3:]
        result["mountpoint"] = []
        if disk["IsBoot"]:
            result["mountpoint"].append("[BOOT]")
        big_result.append(result)
    return big_result


def get_smartctl_status(smartctl_output: str) -> Optional[str]:
    # noinspection PyBroadException
    try:
        return smartctl_get_status(parse_smartctl_output(smartctl_output))
    except BaseException as e:
        logging.error("Failed to parse smartctl output", exc_info=e)
        return None


def find_mounts(el: dict):
    mounts = []
    if el["mountpoint"] is not None:
        mounts.append(el["mountpoint"])
    if "children" in el:
        children = el["children"]
        for child in children:
            mounts += find_mounts(child)
    return mounts


def get_disks(path: Optional[str] = None) -> list:
    # Name is required, otherwise the tree is flattened
    output = subprocess\
        .getoutput(f"lsblk -b -o NAME,PATH,VENDOR,MODEL,SERIAL,HOTPLUG,ROTA,MOUNTPOINT,SIZE -J {path if path else ''}")
    jsonized = json.loads(output)
    if "blockdevices" in jsonized:
        result = jsonized["blockdevices"]
    else:
        result = []
    for el in result:
        mounts = find_mounts(el)
        if "children" in el:
            del el["children"]
        if "name" in el:
            del el["name"]
        el["mountpoint"] = mounts

    return result


TARALLO = None

clients: dict[int, TurboProtocol] = {}
clients_lock = threading.Lock()

disks: dict[str, Disk] = {}
disks_lock = threading.RLock()

running_commands: set[CommandRunner] = set()
running_commands_lock = threading.Lock()

queued_commands: list[QueuedCommand] = []
queued_commands_lock = threading.Lock()


if __name__ == '__main__':
    load_settings()
    if CURRENT_OS == 'win32':
        main()
    else:
        if bool(os.getenv("DAEMONIZE", False)):
            import daemon
            import lockfile
            with daemon.DaemonContext(pidfile=lockfile.FileLock(os.getenv("LOCKFILE_PATH", f'/var/run/{NAME}.pid'))):
                main()
        else:
            main()
