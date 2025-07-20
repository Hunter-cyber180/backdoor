from socket_handlers import socket_recv
from termcolor import colored
import os, ast


def handle_download(client_socket, command) -> bool:
    """
    Handles file download from a client socket.

    Args:
        client_socket: The socket connection to receive data from.
        command: The download command string (may contain optional file path).

    Returns:
        bool: True if download was successful, False otherwise.

    Process:
        1. Receives initial file info data from the socket
        2. Validates the file information (name and size)
        3. Uses the provided path from command or defaults to the sent filename
        4. Receives file data in chunks and writes to disk
        5. Verifies the final file size matches the expected size
        6. Cleans up partial files if any errors occur

    Error Handling:
        - Prints colored error messages for various failure cases
        - Removes partially downloaded files on failure
        - Handles permission errors, size mismatches, and network issues

    Example:
        Successful download prints: "[+] File 'example.txt' downloaded (1.23MB)"
        Failed download prints error messages in red.
    """
    try:
        file_info_data = socket_recv(client_socket)
        if file_info_data.startswith("Error"):
            print(colored(file_info_data, "red"))
            return False

        try:
            file_info = ast.literal_eval(socket_recv(client_socket))
            if (
                not isinstance(file_info, dict)
                or "name" not in file_info
                or "size" not in file_info
            ):
                raise ValueError("Invalid file info format")

        except Exception as e:
            print(colored(f"[!] Error decoding file info: {str(e)}", "red"))
            return False

        file_path = command[9:].strip() or file_info["name"]

        try:
            with open(file_path, "wb") as fp:
                received_bytes = 0
                while received_bytes < file_info["size"]:
                    chunk_data = socket_recv(client_socket)
                    if (
                        chunk_data.startswith("Error")
                        or chunk_data == "[+] File Transfer Complete"
                    ):
                        break
                    fp.write(chunk_data)
                    received_bytes += len(chunk_data)

            if os.path.getsize(file_path) != file_info["size"]:
                os.remove(file_path)
                error_msg = "Error: File size mismatch"
                print(colored(error_msg, "red"))
                return False

            print(
                colored(
                    f"[+] File '{file_path}' downloaded ({file_info['size']/1024/1024:.2f}MB)",
                    "green",
                )
            )
            return True

        except PermissionError:
            error_msg = "Error: Permission denied"
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

        print(colored(error_msg, "red"))
        return False

    except Exception as e:
        print(colored(f"Download failed: {e}", "red"))
        return False
