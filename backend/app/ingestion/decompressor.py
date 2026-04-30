from __future__ import annotations

import logging
import os
import shutil
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
MAX_ARCHIVE_SIZE = 500 * 1024 * 1024  # 500 MB


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
            if f.is_file() and not f.is_symlink():
                results.extend(self.extract(f))
        return results

    def _extract_archive(self, archive_path: Path, depth: int) -> list[FileInfo]:
        if depth > 5:
            logger.warning("嵌套深度超限: %s", archive_path)
            return []
        if archive_path.stat().st_size > MAX_ARCHIVE_SIZE:
            logger.warning("压缩包体积超限: %s (%d bytes)", archive_path, archive_path.stat().st_size)
            return []
        extract_dir = tempfile.mkdtemp()
        try:
            self._do_extract(archive_path, extract_dir)
            results: list[FileInfo] = []
            for f in sorted(Path(extract_dir).rglob("*")):
                if f.is_file() and not f.is_symlink():
                    suffix = f.suffix.lower()
                    if suffix in ARCHIVE_FORMATS:
                        results.extend(self._extract_archive(f, depth + 1))
                    elif suffix in SUPPORTED_FORMATS:
                        results.append(FileInfo(path=f, format=suffix, original_archive=archive_path))
            return results
        except Exception:
            shutil.rmtree(extract_dir, ignore_errors=True)
            raise

    def _do_extract(self, archive_path: Path, dest: str) -> None:
        suffix = archive_path.suffix.lower()
        dest_path = Path(dest)
        if suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                self._validate_zip_members(zf, dest_path)
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

    @staticmethod
    def _validate_zip_members(zf: zipfile.ZipFile, dest: Path) -> None:
        dest_resolved = dest.resolve()
        for member in zf.infolist():
            if member.is_dir():
                continue
            member_path = (dest_resolved / member.filename).resolve()
            if not str(member_path).startswith(str(dest_resolved)):
                raise ValueError(f"zip-slip 检测: {member.filename} 试图逃逸到目标目录外")
            if os.path.islink(member_path) if member_path.exists() else False:
                raise ValueError(f"符号链接检测: {member.filename} 为符号链接")
