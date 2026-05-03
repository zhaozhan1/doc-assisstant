from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser

import uvicorn

from app.config import AppConfig


def _kill_existing(host: str, port: int) -> None:
    """Kill any process already listening on the given port."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        pids = [p for p in result.stdout.strip().splitlines() if p.strip().isdigit()]
        for pid_str in pids:
            pid = int(pid_str)
            if pid != os.getpid():
                os.kill(pid, signal.SIGTERM)
        if pids:
            time.sleep(1)
    except Exception:
        pass


def _open_browser(url: str, host: str, port: int) -> None:
    for _ in range(60):
        time.sleep(1)
        try:
            with socket.create_connection((host, port), timeout=1):
                break
        except OSError:
            continue
    webbrowser.open(url)


def main() -> None:
    config = AppConfig()
    host = config.server.host
    port = config.server.port
    url = f"http://{host}:{port}"

    if getattr(sys, "frozen", False):
        _kill_existing(host, port)

    threading.Thread(target=_open_browser, args=(url, host, port), daemon=True).start()

    if getattr(sys, "frozen", False):
        from app.main import app

        uvicorn.run(app, host=host, port=port)
    else:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            workers=config.server.workers,
        )


if __name__ == "__main__":
    main()
