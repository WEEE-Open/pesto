#!/usr/bin/env python
import json
import subprocess
from dotenv import load_dotenv
from io import StringIO
import os
from twisted.internet import reactor, protocol
from twisted.protocols.basic import LineOnlyReceiver
import threading
import collections

clients = dict()
clients_lock = threading.Lock()

# TODO: proper queue, where dischi are first piallati then smartclati then whatever
# TODO: save commands list for those long running commands, to display it
commands_list = collections.deque()
commands_list_event = threading.Event()
commands_list_lock = threading.Lock()


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
                if not self._go:
                    break
                if commands_list_event.isSet():
                    with commands_list_lock:
                        try:
                            command = commands_list.popleft()
                            # TODO: launch slow commands in yet another thread, so this one is not blocked
                            self.exec_command(command[0], command[1], command[2])
                        except IndexError:
                            pass

                    with commands_list_lock:
                        if len(commands_list) <= 0:
                            commands_list_event.clear()
            except:
                print("BIG ERROR")
                with commands_list_lock:
                    if len(commands_list) <= 0:
                        commands_list_event.clear()

    def exec_command(self, cmd: str, args: str, the_id: int):
        print(f"[{the_id}] Received command {cmd}{' with args' if len(args) > 0 else ''}")
        # This part doesn't work
        if cmd == 'smartctl':
            param = self.get_smarctl(args)
            self.send_msg(the_id, f"smartctl {param}")
        elif cmd == 'get_disks':
            param = self.get_disks()
            self.send_msg(the_id, f"get_disks {param}")
        elif cmd == 'get_disks_win':
            param = get_disks_win()
            self.send_msg(the_id, f"get_disks_win {param}")
        elif cmd == 'ping':
            self.send_msg(the_id, f"pong")
        else:
            param = json.dumps({"message": "Unrecognized command", "command": cmd}, separators=(',', ':'), indent=None)
            self.send_msg(the_id, f"error {param}")

    def get_disks(self):
        # Name is required, otherwise the tree is flattened
        output = subprocess.getoutput("lsblk -o NAME,PATH,VENDOR,MODEL,SERIAL,HOTPLUG,ROTA,MOUNTPOINT -J")
        jsonized = json.loads(output)
        if "blockdevices" in jsonized:
            result = jsonized["blockdevices"]
        else:
            result = []
        for el in result:
            mounts = self.find_mounts(el)
            if "children" in el:
                del el["children"]
            if "name" in el:
                del el["name"]
            el["mountpoint"] = mounts

        return json.dumps(result, separators=(',', ':'), indent=None)

    @staticmethod
    def get_smarctl(args):
        exitcode, output = subprocess.getstatusoutput("sudo smartctl -a " + args)
        jsonize = {
            "disk": args,
            "exitcode": exitcode,
            "output": output,
        }
        return json.dumps(jsonize, separators=(',', ':'), indent=None)

    def find_mounts(self, el: dict):
        mounts = []
        if el["mountpoint"] is not None:
            mounts.append(el["mountpoint"])
        if "children" in el:
            children = el["children"]
            for child in children:
                mounts += self.find_mounts(child)
        return mounts

    def send_msg(self, client_id: int, msg: str):
        with clients_lock:
            thread = clients.get(client_id)
            if thread is None:
                print(f"[{client_id}] Connection already closed while trying to send a message")
            else:
                thread: TurboHandler
                self._reactor.callFromThread(TurboHandler.send_msg, thread, msg)

    def stop_asap(self):
        self._go = False
        commands_list_event.set()
        self.join(self._sleep * 2)


class TurboHandler(LineOnlyReceiver):
    def __init__(self):
        self._id = -1

    def connectionMade(self):
        self._id = self.factory.conn_id
        self.factory.conn_id += 1
        with commands_list_lock:
            with clients_lock:
                clients[self._id] = self
        print(f"[{str(self._id)}] Client connected")

    def connectionLost(self, reason=protocol.connectionDone):
        print(f"[{str(self._id)}] Client disconnected")
        with commands_list_lock:
            with clients_lock:
                del clients[self._id]

    def lineReceived(self, line):
        line = line.decode('utf-8').strip()
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
        self.sendLine(response.encode('utf-8'))


def main():
    load_settings()
    ip = os.getenv("IP")
    port = os.getenv("PORT")

    ch = None

    try:
        factory = protocol.ServerFactory()
        factory.protocol = TurboHandler
        factory.conn_id = 0

        print(f"Listening on {ip} port {port}")
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
    load_dotenv('~/.conf/WeeeOpen/turbofresa.env')
    load_dotenv('/etc/turbofresa.env')
    # Defaults
    config = StringIO("IP=127.0.0.1\nPORT=1030")
    load_dotenv(stream=config)


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
    return json.dumps(drive, separators=(',', ':'), indent=None)


if __name__ == '__main__':
    main()
