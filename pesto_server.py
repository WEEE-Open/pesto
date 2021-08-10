#!/usr/bin/env python
import json
import subprocess
from dotenv import load_dotenv
from io import StringIO
import os
import socketserver
import threading
import collections

sockets_list = dict()
sockets_list_id = 0
sockets_list_lock = threading.Lock()

commands_list = collections.deque()
commands_list_event = threading.Event()
commands_list_lock = threading.Lock()


class TurbofresaServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class CommandRunner(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.thread_name = "CommandRunner"
        self._go = True
        self._sleep = 5.0

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
                            exec_command(command[0], command[1], command[2])
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

    def stop_asap(self):
        self._go = False
        commands_list_event.set()
        self.join(self._sleep * 2)


class TurboHandler(socketserver.StreamRequestHandler):
    def handle(self):
        conn_id = self.create_id()

        client_addr = self.client_address
        print(f'Connected to {client_addr}, id {conn_id}')
        while True:
            data = self.rfile.readline()
            if not data:
                # Connection closed
                break

            # Some command
            command = data.decode('utf-8').strip()

            # Exit command
            if command.lower() == 'exit':
                break

            self.enqueue_command(command, conn_id)

        with sockets_list_lock:
            del sockets_list[conn_id]
        # print(f'Closed connection to {client_addr}')

    def send_message(self, text: str):
        self.wfile.write(f"{text}\n".encode('utf-8'))

    def create_id(self):
        with sockets_list_lock:
            global sockets_list_id

            while sockets_list_id in sockets_list:
                sockets_list_id += 1

            the_chosen_one = sockets_list_id
            sockets_list[the_chosen_one] = self
            # Do not reuse it
            sockets_list_id += 1
        return the_chosen_one

    @staticmethod
    def enqueue_command(cmd: str, conn_id: int):
        parts = cmd.split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1] if 1 in parts else ''
        with commands_list_lock:
            commands_list.append((cmd, args, conn_id))
            commands_list_event.set()


def exec_command(cmd: str, args: str, id: int):
    # This part doesn't work
    if cmd == 'smartctl':
        output = subprocess.getoutput("smartctl -a " + args)
        # return output
    elif cmd == 'get_disks':
        output = subprocess.getoutput("lsblk -d")
        disks = get_disks(output)
        # return disks
    elif cmd == 'get_disks_win':
        pass
        # return get_disks_win()
    elif cmd == 'ping':
        self.send_message(f"pong")
    else:
        param = json.dumps({"message": "Unrecognized command"}, separators=(',', ':'), indent=None)
        self.send_message(f"error {param}")


def main():
    load_settings()
    ip = os.getenv("IP")
    port = os.getenv("PORT")

    ch = CommandRunner()
    ch.start()

    try:
        with TurbofresaServer((ip, int(port)), TurboHandler) as server:
            print(f"Listening on {ip} port {port}")
            server.allow_reuse_address = True
            server.serve_forever()
    except KeyboardInterrupt:
        print("KeyboardInterrupt, terminating")
        server.shutdown()
    finally:
        ch.stop_asap()


def load_settings():
    # Load in order each file if exists, variables are not overwritten
    load_dotenv('.env')
    load_dotenv('~/.conf/WeeeOpen/turbofresa.env')
    load_dotenv('/etc/turbofresa.env')
    # Defaults
    config = StringIO("IP=127.0.0.1\nPORT=1030")
    load_dotenv(stream=config)


def get_disks(lsblk):
    result = []
    for line in lsblk:
        if line[0] == 's':
            temp = " ".join(line.split())
            temp = temp.split(" ")
            result.append([temp[0], temp[3]])
    return str(result)


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
    return str(drive)


if __name__ == '__main__':
    main()
