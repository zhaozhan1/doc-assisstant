from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from app.ingestion.decompressor import Decompressor


@pytest.fixture
def decompressor() -> Decompressor:
    return Decompressor()


@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    f = tmp_path / "test.txt"
    f.write_text("hello world", encoding="utf-8")
    return f


@pytest.fixture
def sample_zip(tmp_path: Path) -> Path:
    inner = tmp_path / "inner.txt"
    inner.write_text("inner content", encoding="utf-8")
    zip_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(inner, "inner.txt")
    return zip_path


@pytest.fixture
def nested_zip(tmp_path: Path) -> Path:
    inner = tmp_path / "doc.txt"
    inner.write_text("nested content", encoding="utf-8")
    inner_zip = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner_zip, "w") as zf:
        zf.write(inner, "doc.txt")
    outer_zip = tmp_path / "outer.zip"
    with zipfile.ZipFile(outer_zip, "w") as zf:
        zf.write(inner_zip, "inner.zip")
    return outer_zip


class TestSingleFile:
    def test_supported_format(self, decompressor: Decompressor, sample_txt: Path) -> None:
        results = decompressor.extract(sample_txt)
        assert len(results) == 1
        assert results[0].format == ".txt"
        assert results[0].path == sample_txt
        assert results[0].original_archive is None

    def test_unsupported_format(self, decompressor: Decompressor, tmp_path: Path) -> None:
        f = tmp_path / "test.xyz"
        f.write_text("unknown")
        results = decompressor.extract(f)
        assert results == []


class TestZipExtract:
    def test_extracts_files_from_zip(self, decompressor: Decompressor, sample_zip: Path) -> None:
        results = decompressor.extract(sample_zip)
        assert len(results) == 1
        assert results[0].format == ".txt"
        assert results[0].original_archive == sample_zip

    def test_extracts_nested_zip(self, decompressor: Decompressor, nested_zip: Path) -> None:
        results = decompressor.extract(nested_zip)
        assert len(results) == 1
        assert results[0].format == ".txt"
        assert "nested content" in results[0].path.read_text()


class TestDirectory:
    def test_scans_directory(self, decompressor: Decompressor, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.pdf").write_text("b")
        (tmp_path / "c.xyz").write_text("c")
        results = decompressor.extract(tmp_path)
        formats = {r.format for r in results}
        assert formats == {".txt", ".pdf"}
        assert len(results) == 2


class TestSecurity:
    def test_zip_slip_rejected(self, decompressor: Decompressor, tmp_path: Path) -> None:
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../../etc/passwd", "pwned")
        with pytest.raises(ValueError, match="zip-slip"):
            decompressor.extract(zip_path)

    def test_oversized_archive_rejected(
        self, decompressor: Decompressor, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import app.ingestion.decompressor as mod

        monkeypatch.setattr(mod, "MAX_ARCHIVE_SIZE", 10)
        zip_path = tmp_path / "big.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("data.txt", "x" * 100)
        results = decompressor.extract(zip_path)
        assert results == []

    def test_symlink_in_directory_skipped(self, decompressor: Decompressor, tmp_path: Path) -> None:
        real = tmp_path / "real.txt"
        real.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(real)
        results = decompressor.extract(tmp_path)
        assert len(results) == 1
        assert results[0].path == real

    def test_zip_slip_path_traversal_rejected(self, decompressor: Decompressor, tmp_path: Path) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("foo/../../bar.txt", "traversal")
        zip_path = tmp_path / "traversal.zip"
        zip_path.write_bytes(buf.getvalue())
        with pytest.raises(ValueError, match="zip-slip"):
            decompressor.extract(zip_path)
