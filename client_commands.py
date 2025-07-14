from socket_handlers import *
from urllib.parse import unquote
import os, base64, binascii, requests
from pathvalidate import sanitize_filename, sanitize_filepath


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


def urldownload(url, max_size_mb=10, timeout=30):
    try:
        with requests.head(url, timeout=timeout) as head_response:
            head_response.raise_for_status()

            if head_response.status_code != 200:
                socket_send(
                    f"Error: Server returned status code {head_response.status_code}"
                )
                return "[!] Error"

            content_type = head_response.headers.get("Content-Type", "")
            if not content_type.startswith(("image/", "application/octet-stream")):
                socket_send(f"Error: Unsupported content type: {content_type}")
                return "[!] Error"

            content_length = int(head_response.headers.get("Content-Length", 0))
            max_size_bytes = max_size_mb * 1024 * 1024
            if content_length > max_size_bytes:
                socket_send(
                    f"Error: File size exceeds maximum allowed size ({max_size_mb}MB)"
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
                            socket_send(f"Error: File size exceeded during download")
                            return "[!] Error"
            socket_send(
                f"'{file_name}' successfully downloaded ({downloaded_size/1024:.2f} KB)"
            )
            return True

    except requests.exceptions.RequestException as e:
        return f"[!] Error: Network error: {str(e)}"
    except IOError as e:
        return f"[!] Error: File system error: {str(e)}"
    except Exception as e:
        return f"[!] Error: Unexpected error: {str(e)}"
