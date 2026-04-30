from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path

from app.models.document import FileInfo

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {
    ".docx",
    ".pdf",
    ".xlsx",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".txt",
}
ARCHIVE_FORMATS = {".zip", ".rar", ".7z"}


class Decompressor:
    def extract(self, path: Path) -> list[FileInfo]:
        path = Path(path)
        if path.is_dir():
            return self._scan_directory(path)
        suffix = path.suffix.lower()
        if suffix in ARCHIVE_FORMATS:
            return self._extract_archive(path, depth=0)
        if suffix in SUPPORTED_FORMATS:
            return [FileInfo(path=path, format=suffix, original_archive=None)]
        return []

    def _scan_directory(self, directory: Path) -> list[FileInfo]:
        results: list[FileInfo] = []
        for f in sorted(directory.rglob("*")):
            if f.is_file():
                results.extend(self.extract(f))
        return results

    def _extract_archive(self, archive_path: Path, depth: int) -> list[FileInfo]:
        if depth > 5:
            logger.warning("嵌套深度超限: %s", archive_path)
            return []
        extract_dir = tempfile.mkdtemp()
        self._do_extract(archive_path, extract_dir)
        results: list[FileInfo] = []
        for f in sorted(Path(extract_dir).rglob("*")):
            if f.is_file():
                suffix = f.suffix.lower()
                if suffix in ARCHIVE_FORMATS:
                    results.extend(self._extract_archive(f, depth + 1))
                elif suffix in SUPPORTED_FORMATS:
                    results.append(FileInfo(path=f, format=suffix, original_archive=archive_path))
        return results

    def _do_extract(self, archive_path: Path, dest: str) -> None:
        suffix = archive_path.suffix.lower()
        if suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest)
        elif suffix == ".7z":
            import py7zr

            with py7zr.SevenZipFile(archive_path, "r") as sz:
                sz.extractall(dest)
        elif suffix == ".rar":
            from pyunpack import Archive

            Archive(str(archive_path)).extractall(dest)
        else:
            logger.warning("不支持的压缩格式: %s", suffix)
