from socket_handlers import socket_recv
from termcolor import colored
import base64, os, ast


def handle_download(client_socket, command):
    try:
        file_info_data = socket_recv(client_socket)
        if file_info_data.startswith("Error"):
            print(colored(file_info_data, "red"))
            return False

    except:
        pass
