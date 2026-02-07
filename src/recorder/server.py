# src/recorder/serve_dir.py

import os
import threading
import socket
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial


class TempRecordingServer:
    """
    Lightweight temporary HTTP server to serve .wav files
    from a given directory (default: ./recordings).

    Usage:
        server = TempRecordingServer(logger)
        server.start()
        ...
        server.stop()
    """

    def __init__(self, logger, directory="recordings", host="0.0.0.0", port=0):
        self.logger = logger
        self.directory = os.path.abspath(directory)
        self.host = host
        self.port = port  # 0 = auto-assign free port

        self._httpd = None
        self._thread = None
        self._running = False

    # -------------------------
    # Public API
    # -------------------------

    def start(self):
        if self._running:
            self.logger.warning("Recording server already running.")
            return

        if not os.path.isdir(self.directory):
            self.logger.warning(f"Directory not found: {self.directory}")
            return

        handler = partial(SimpleHTTPRequestHandler, directory=self.directory)

        try:
            self._httpd = ThreadingHTTPServer((self.host, self.port), handler)

            # If port was 0, fetch the auto-assigned port
            self.port = self._httpd.server_address[1]

            self._thread = threading.Thread(
                target=self._httpd.serve_forever,
                daemon=True,
                name="RecordingHTTPServer",
            )
            self._thread.start()

            self._running = True

            ip = self._get_local_ip()
            self.logger.info(
                f"Recording server started at http://{ip}:{self.port}"
            )

        except Exception as e:
            self.logger.exception(f"Failed to start recording server: {e}")
            self._running = False

    def stop(self):
        if not self._running:
            return

        try:
            self._httpd.shutdown()
            self._httpd.server_close()

            if self._thread:
                self._thread.join(timeout=5)

            self.logger.info("Recording server stopped.")

        except Exception:
            self.logger.exception("Error while stopping recording server.")
        finally:
            self._httpd = None
            self._thread = None
            self._running = False

    @property
    def running(self):
        return self._running

    # -------------------------
    # Helpers
    # -------------------------

    def _get_local_ip(self):
        """
        Tries to determine local IP for logging.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "localhost"
