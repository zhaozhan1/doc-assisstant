from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.paths import get_data_dir, resolve_path


class TestGetDataDir:
    def test_dev_mode_returns_cwd_based(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        result = get_data_dir()
        assert result == Path.cwd() / "doc-assistant"

    def test_frozen_mode_returns_library_support(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        result = get_data_dir()
        assert result == Path.home() / "Library" / "Application Support" / "doc-assistant"

    def test_creates_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        result = get_data_dir()
        assert result.is_dir()


class TestResolvePath:
    def test_absolute_path_unchanged(self) -> None:
        assert resolve_path("/absolute/path") == "/absolute/path"

    def test_relative_path_resolved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        result = resolve_path("./data/chroma_db")
        assert "data/chroma_db" in result
        assert Path(result).is_absolute()

    def test_dot_only_resolved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        result = resolve_path("./logs/app.log")
        assert "logs/app.log" in result
