import socket, base64
from termcolor import colored


def run_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(colored("[+] Server Socket Created.", "blue"))
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(colored("[+] Server Is Listening...", "blue"))

if "__main__" == __name__:
    run_server(host="0.0.0.0", port=6018)
