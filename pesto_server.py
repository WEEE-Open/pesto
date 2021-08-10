import subprocess
import socket

LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 20001
BUFFER_SIZE = 1024

def main():
    # Create datagram socket
    UDP_server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

    # Bind to address and IP
    UDP_server_socket.bind((LOCAL_IP, LOCAL_PORT))

    print("UDP server up and listening...")

    while(True):
        bytes_address_pair = UDP_server_socket.recvfrom(BUFFER_SIZE)
        message_from_client = bytes_address_pair[0]
        client_address = bytes_address_pair[1]
        client_msg = "Command from client: {}".format(message_from_client.decode('utf-8'))
        client_IP = "Client IP: {}".format(client_address)

        print(client_msg)

        result = exec_command(message_from_client.decode('utf-8'))
        print(result)
        print("\n\n\nTOTAL BYTE TO SEND: " + str(len(result)))
        print(client_IP)
        BYTES_TO_SEND = result.encode('utf-8')
        UDP_server_socket.sendto(BYTES_TO_SEND, client_address)


def exec_command(cmd):
    if 'smartctl' in cmd:
        drive = cmd.split()[2]
        output = subprocess.getoutput("smartctl -a " + drive)
        return output
    elif cmd == 'get_disks':
        output = subprocess.getoutput("lsblk -d")
        disks = get_disks(output)
        return disks
    elif cmd == 'get_disks_win':
        return get_disks_win()


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
