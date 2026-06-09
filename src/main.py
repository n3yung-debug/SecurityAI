"""Entry point for the Operations Assistant desktop program.

Starts the local web server, then opens the app in the default web browser.
Designed to be packaged into a single Windows .exe with PyInstaller.
"""

from __future__ import annotations

import socket
import threading
import webbrowser

from waitress import serve

from .server import create_app


def _find_free_port(preferred: int = 8731) -> int:
    """Use a fixed port if available, otherwise let the OS pick one."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]


def main() -> None:
    app = create_app()
    port = _find_free_port()
    url = f"http://127.0.0.1:{port}/"

    # Open the browser a moment after the server starts accepting connections.
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    print("=" * 60)
    print("  Operations Assistant is running.")
    print(f"  If your browser did not open, go to: {url}")
    print("  Keep this window open while you use the program.")
    print("  Close this window to shut the program down.")
    print("=" * 60)

    # Single local user, so one thread is plenty and keeps memory low.
    serve(app, host="127.0.0.1", port=port, threads=4)


if __name__ == "__main__":
    main()
