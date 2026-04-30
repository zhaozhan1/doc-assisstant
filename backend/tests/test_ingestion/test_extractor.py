from __future__ import annotations

from pathlib import Path

import pytest

from app.config import OCRConfig
from app.ingestion.extractor import Extractor
from app.models.document import FileInfo


@pytest.fixture
def extractor() -> Extractor:
    return Extractor(OCRConfig())


class TestTxtExtract:
    def test_extracts_text(self, extractor: Extractor, fixtures_dir: Path) -> None:
        fi = FileInfo(path=fixtures_dir / "sample.txt", format=".txt")
        doc = extractor.extract(fi)
        assert "测试文本" in doc.text
        assert doc.source_path == fi.path


class TestDocxExtract:
    def test_extracts_text_and_structure(self, extractor: Extractor, fixtures_dir: Path) -> None:
        fi = FileInfo(path=fixtures_dir / "sample.docx", format=".docx")
        doc = extractor.extract(fi)
        assert "正文内容" in doc.text
        assert len(doc.structure) >= 1
        assert doc.structure[0].level == 1
        assert "测试标题" in doc.structure[0].text


class TestXlsxExtract:
    def test_extracts_tabular_data(self, extractor: Extractor, fixtures_dir: Path) -> None:
        fi = FileInfo(path=fixtures_dir / "sample.xlsx", format=".xlsx")
        doc = extractor.extract(fi)
        assert "张三" in doc.text
        assert "办公室" in doc.text


class TestPptxExtract:
    def test_extracts_slide_text(self, extractor: Extractor, fixtures_dir: Path) -> None:
        fi = FileInfo(path=fixtures_dir / "sample.pptx", format=".pptx")
        doc = extractor.extract(fi)
        assert "PPT" in doc.text or "内容" in doc.text


class TestUnsupportedFormat:
    def test_raises_on_unsupported_format(self, extractor: Extractor, tmp_path: Path) -> None:
        fi = FileInfo(path=tmp_path / "test.xyz", format=".xyz")
        with pytest.raises(ValueError, match="不支持的格式"):
            extractor.extract(fi)


class TestEmptyFile:
    def test_handles_empty_txt(self, extractor: Extractor, tmp_path: Path) -> None:
        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")
        fi = FileInfo(path=empty, format=".txt")
        doc = extractor.extract(fi)
        assert doc.text == ""
