from socket_handlers import socket_recv
from termcolor import colored
import base64, os, ast


def handle_download(client_socket, command):
    try:
        file_info_data = socket_recv(client_socket)
        if file_info_data.startswith("Error"):
            print(colored(file_info_data, "red"))
            return False

        try:
            file_info = ast.literal_eval(socket_recv(client_socket))
            if not isinstance(file_info, dict) or 'name' not in file_info or 'size' not in file_info:
                raise ValueError("Invalid file info format")
                
        except Exception as e:
            print(colored(f"[!] Error decoding file info: {str(e)}", "red"))
            return False

        file_path = command[9:].strip() or file_info["name"]

    except:
        pass
