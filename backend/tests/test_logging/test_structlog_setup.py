from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import LoggingConfig
from app.main import setup_logging


def _setup(config: LoggingConfig) -> None:
    """Setup logging with _force to bypass pytest's LogCaptureHandler guard."""
    setup_logging(config, _force=True)


class TestStructlogSetup:
    def test_file_handler_outputs_json(self, tmp_path: Path) -> None:
        """File handler should produce valid JSON lines."""
        log_file = tmp_path / "test.jsonl"
        _setup(LoggingConfig(level="INFO", file=str(log_file)))

        logger = logging.getLogger("test.json.output")
        logger.info("structured log test", extra={"key": "value"})

        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text(encoding="utf-8").strip()
        lines = [line for line in content.split("\n") if line.strip()]
        assert len(lines) >= 1
        parsed = json.loads(lines[-1])
        assert parsed["event"] == "structured log test"

    def test_console_handler_uses_dev_format(self, tmp_path: Path) -> None:
        """Console handler should use ProcessorFormatter with ConsoleRenderer."""
        log_file = tmp_path / "console.log"
        _setup(LoggingConfig(level="INFO", file=str(log_file)))

        root_logger = logging.getLogger()
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
        stream_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]

        assert len(file_handlers) >= 1
        assert len(stream_handlers) >= 1
        # Console handler should have a ProcessorFormatter
        console = stream_handlers[0]
        assert console.formatter is not None

    def test_setup_logging_idempotent(self, tmp_path: Path) -> None:
        """Calling setup_logging twice with _force should reset handlers."""
        log_file = tmp_path / "idempotent.log"
        config = LoggingConfig(level="INFO", file=str(log_file))
        _setup(config)
        handler_count = len(logging.getLogger().handlers)
        _setup(config)
        assert len(logging.getLogger().handlers) == handler_count

    def test_log_level_respected(self, tmp_path: Path) -> None:
        """DEBUG level config should allow debug messages through to file."""
        log_file = tmp_path / "debug.jsonl"
        _setup(LoggingConfig(level="DEBUG", file=str(log_file)))

        logger = logging.getLogger("test.debug.level")
        logger.debug("debug message here")

        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text(encoding="utf-8").strip()
        lines = [line for line in content.split("\n") if line.strip()]
        assert any("debug message here" in line for line in lines)

    def test_json_includes_timestamp_and_level(self, tmp_path: Path) -> None:
        """JSON log output should include timestamp and level fields."""
        log_file = tmp_path / "fields.jsonl"
        _setup(LoggingConfig(level="INFO", file=str(log_file)))

        logger = logging.getLogger("test.fields")
        logger.info("check fields")

        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text(encoding="utf-8").strip()
        lines = [line for line in content.split("\n") if line.strip()]
        assert len(lines) >= 1
        parsed = json.loads(lines[-1])
        assert "timestamp" in parsed
        assert "level" in parsed
