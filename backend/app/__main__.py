from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from app.config import AppConfig


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
