"""Entry point for the Operations Assistant host program.

Runs on ONE PC (the host). It serves the shared assistant to everyone on the
local network and opens a management window on the host itself.

Designed to be packaged into a single Windows .exe with PyInstaller.
"""

from __future__ import annotations

import socket
import threading
import webbrowser

from waitress import serve

from . import ai
from .server import create_app

PORT = 8731


def _lan_ip() -> str:
    """Best-effort guess of this machine's address on the local network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No traffic is actually sent; this just picks the outbound interface.
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def _ai_line() -> str:
    st = ai.status(force=True)
    if st.get("chat_ready"):
        extra = " + smart search" if st.get("embed_ready") else ""
        return f"Local AI: ON  (model: {st['chat_model']}{extra})"
    if st.get("reachable"):
        return (
            f"Local AI: Ollama running but model '{st['chat_model']}' not found. "
            "Run setup-ai.bat to install it."
        )
    return "Local AI: OFF (using plain search). Install Ollama to enable smart answers."


def main() -> None:
    app = create_app()
    ip = _lan_ip()
    hostname = socket.gethostname()
    host_url = f"http://localhost:{PORT}/"

    # Open the management window on the host after the server is up.
    threading.Timer(1.0, lambda: webbrowser.open(host_url)).start()

    print("=" * 66)
    print("  Operations Assistant -- HOST is running")
    print("-" * 66)
    print(f"  {_ai_line()}")
    print("-" * 66)
    print("  Share this address with everyone on the network (ask-only):")
    print(f"      http://{ip}:{PORT}/        (by IP)")
    print(f"      http://{hostname}:{PORT}/  (by computer name)")
    print()
    print("  To MANAGE knowledge, use this host PC at:")
    print(f"      {host_url}")
    print("-" * 66)
    print("  Keep this window OPEN. Closing it stops the Assistant for everyone.")
    print("  First time? You may need to allow the app through Windows Firewall")
    print("  (run allow-firewall.bat once, as administrator).")
    print("=" * 66)

    # Listen on all interfaces so other PCs on the LAN can connect.
    serve(app=app, host="0.0.0.0", port=PORT, threads=8)


if __name__ == "__main__":
    main()
