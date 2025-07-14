from socket_handlers import *
from urllib.parse import unquote
import os, base64, binascii, requests
from pathvalidate import sanitize_filename


def pwd(socket):
    socket_send(socket, os.getcwd().encode("utf-8"))


def upload(socket, command):
    try:
        # Get file path from command (safer than direct slicing)
        file_path = command.strip()
        if not file_path:
            socket_send(socket, "Error: No file path specified")
            return False

        # Validate file path (basic security check)
        if any(
            char in file_path
            for char in ["..", "~", "/", "\\"]
            if char not in os.path.basename(file_path)
        ):
            socket_send(socket, "Error: Invalid file path")
            return False

        # Receive file data
        data = socket_recv(socket)

        # Check if file exists to avoid overwriting
        if os.path.exists(file_path):
            socket_send(socket, f"Error: File {file_path} already exists")
            return False

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
