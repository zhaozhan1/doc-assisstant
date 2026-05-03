from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn

from app.config import AppConfig


def _open_browser(url: str, delay: float = 1.5) -> None:
    time.sleep(delay)
    webbrowser.open(url)


def main() -> None:
    config = AppConfig()
    url = f"http://{config.server.host}:{config.server.port}"
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    uvicorn.run(
        "app.main:app",
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
    )


if __name__ == "__main__":
    main()
