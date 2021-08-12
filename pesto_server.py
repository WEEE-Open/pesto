#!/usr/bin/env python
import json
import subprocess
from typing import Optional

from pytarallo import Tarallo
from dotenv import load_dotenv
from io import StringIO
import os
from twisted.internet import reactor, protocol
from twisted.protocols.basic import LineOnlyReceiver
import threading
import collections
import logging

NAME = "turbofresa"

clients = dict()
clients_lock = threading.Lock()

# TODO: proper queue, where dischi are first piallati then smartclati then whatever
# TODO: save commands list for those long running commands, to display it
commands_list = collections.deque()
commands_list_event = threading.Event()
commands_list_lock = threading.Lock()

TARALLO = None
disks = {}


class CommandRunner(threading.Thread):
    def __init__(self, reac: reactor):
        threading.Thread.__init__(self)
        self.thread_name = "CommandRunner"
        self._go = True
        self._sleep = 5.0
        self._reactor = reac

    def run(self):
        while self._go:
            try:
                commands_list_event.wait(self._sleep)
                if commands_list_event.isSet():
                    with commands_list_lock:
                        if self.has_more_commands_or_unset_event():
                            try:
                                command = commands_list.popleft()
                                # TODO: launch slow commands in yet another thread, so this one is not blocked
                                self.exec_command(command[0], command[1], command[2])
                            except IndexError:
                                pass
            except BaseException as e:
                logging.getLogger(NAME).error("BIG ERROR", exc_info=e)
                with commands_list_lock:
                    self.has_more_commands_or_unset_event()

    @staticmethod
    def has_more_commands_or_unset_event() -> bool:
        if len(commands_list) <= 0:
            commands_list_event.clear()
            return False
        return True

    def exec_command(self, cmd: str, args: str, the_id: int):
        logging.getLogger(NAME)\
            .debug(f"[{the_id}] Received command {cmd}{' with args' if len(args) > 0 else ''}")
        param = None
        if cmd == 'smartctl':
            param = get_smarctl(args)
        elif cmd == 'get_disks':
            param = self.get_disks_to_send(the_id)
        elif cmd == 'get_disks_win':
            param = get_disks_win()
        elif cmd == 'ping':
            cmd = "pong"
        else:
            param = {"message": "Unrecognized command", "command": cmd}
            # Do not move this line above the other, cmd has to be overwritten here
            cmd = "error"
        self.send_msg(the_id, cmd, param)

    @staticmethod
    def _encode_param(param):
        return json.dumps(param, separators=(',', ':'), indent=None)

    def send_msg(self, client_id: int, cmd: str, param=None):
        with clients_lock:
            thread = clients.get(client_id)
            if thread is None:
                logging.getLogger(NAME)\
                    .info(f"[{client_id}] Connection already closed while trying to send {cmd}")
            else:
                thread: TurboHandler
                j_param = self._encode_param(param)
                self._reactor.callFromThread(TurboHandler.send_msg, thread, f"{cmd} {j_param}")

    def stop_asap(self):
        self._go = False
        commands_list_event.set()
        self.join(self._sleep * 2)

    def get_disks_to_send(self, the_id: int):
        result = []
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
                disks[disk]: Disk
                # noinspection PyBroadException
                try:
                    disks[disk].update_if_needed()
                except ErrorThatCanBeManuallyFixed as e:
                    self.send_msg(the_id, "error_that_can_be_manually_fixed", {"message": str(e), "disk": disk})
                except BaseException:
                    pass
                result.append(disks[disk].serialize_disk())
        return result


class TurboHandler(LineOnlyReceiver):
    def __init__(self):
        self._id = -1
        self.delimiter = b'\n'
        self._delimiter_found = False

    def connectionMade(self):
        self._id = self.factory.conn_id
        self.factory.conn_id += 1
        with commands_list_lock:
            with clients_lock:
                clients[self._id] = self
        logging.getLogger(NAME).debug(f"[{str(self._id)}] Client connected")

    def connectionLost(self, reason=protocol.connectionDone):
        logging.getLogger(NAME).debug(f"[{str(self._id)}] Client disconnected")
        with commands_list_lock:
            with clients_lock:
                del clients[self._id]

    def lineReceived(self, line):
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError as e:
            logging.getLogger(NAME).warning(f"[{str(self._id)}] Oh no, UnicodeDecodeError!", exc_info=e)
            return

        # \n is stripped by twisted, but with \r\n the \r is still there
        if not self._delimiter_found:
            if len(line) > 0 and line[-1] == '\r':
                self.delimiter = b'\r\n'
                logging.getLogger(NAME).debug(f"[{str(self._id)}] Client has delimiter \\r\\n")
            else:
                logging.getLogger(NAME).debug(f"[{str(self._id)}] Client has delimiter \\n")
            self._delimiter_found = True

        # Strip \r on first message (if \r\n) and any trailing whitespace
        line = line.strip()
        if line.startswith('exit'):
            self.transport.loseConnection()
        else:
            parts = line.split(' ', 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ''
            with commands_list_lock:
                commands_list.append((cmd, args, self._id))
                commands_list_event.set()

    def send_msg(self, response: str):
        if self._delimiter_found:
            self.sendLine(response.encode('utf-8'))
        else:
            logging.getLogger(NAME)\
                .warning(f"[{str(self._id)}] Cannot send command to client due to unknown delimiter: {response}")


class Disk:
    def __init__(self, lsblk, tarallo: Optional[Tarallo.Tarallo]):
        self._lsblk = lsblk
        if "path" not in self._lsblk:
            raise RuntimeError("lsblk did not provide path for this disk: " + self._lsblk)
        self._path = str(self._lsblk["path"])
        self._code = None
        self._item = None

        self._tarallo = tarallo
        self._get_code(False)
        self._get_item()

    def update_if_needed(self):
        if not self._code:
            self._get_code(True)
        self._get_item()

    def serialize_disk(self):
        result = self._lsblk
        result["code"] = self._code
        return result

    def _get_code(self, stop_on_error: bool = True):
        if self._tarallo is None:
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


def scan_for_disks():
    logging.debug("Scanning for disks")
    disks_lsblk = get_disks()
    for disk in disks_lsblk:
        if "path" not in disk:
            logging.warning("Disk has no path, ignoring: " + disk)
            continue
        path = disk["path"]
        # noinspection PyBroadException
        try:
            disks[path] = Disk(disk, TARALLO)
        except BaseException as e:
            logging.warning("Exception while scanning disk, skipping", exc_info=e)


def main():
    load_settings()
    scan_for_disks()
    ip = os.getenv("IP")
    port = os.getenv("PORT")

    ch = None

    try:
        factory = protocol.ServerFactory()
        factory.protocol = TurboHandler
        factory.conn_id = 0

        logging.getLogger(NAME).info(f"Listening on {ip} port {port}")
        # noinspection PyUnresolvedReferences
        reactor.listenTCP(int(port), factory, interface=ip)

        ch = CommandRunner(reactor)
        ch.start()

        # noinspection PyUnresolvedReferences
        reactor.run()
    except KeyboardInterrupt:
        print("KeyboardInterrupt, terminating")
    finally:
        if ch is not None:
            ch.stop_asap()


def load_settings():
    # Load in order each file if exists, variables are not overwritten
    load_dotenv('.env')
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


def get_disks_win():
    label = []
    size = []
    drive = []
    for line in subprocess.getoutput("wmic logicaldisk get caption").splitlines():
        if line.rstrip() != 'Caption' and line.rstrip() != '':
            label.append(line.rstrip())
    for line in subprocess.getoutput("wmic logicaldisk get size").splitlines():
        if line.rstrip() != 'Size' and line.rstrip() != '':
            size.append(line)
    for idx, line in enumerate(size):
        drive += [[label[idx], line]]
    return drive


def get_smarctl(args):
    exitcode, output = subprocess.getstatusoutput("sudo smartctl -a " + args)
    return {
        "disk": args,
        "exitcode": exitcode,
        "output": output,
    }


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
        .getoutput(f"lsblk -o NAME,PATH,VENDOR,MODEL,SERIAL,HOTPLUG,ROTA,MOUNTPOINT -J {path if path else ''}")
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


if __name__ == '__main__':
    main()
