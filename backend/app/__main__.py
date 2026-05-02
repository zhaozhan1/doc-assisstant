from __future__ import annotations

import uvicorn

from app.config import AppConfig


def main() -> None:
    config = AppConfig()
    uvicorn.run(
        "app.main:app",
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
    )


if __name__ == "__main__":
    main()
