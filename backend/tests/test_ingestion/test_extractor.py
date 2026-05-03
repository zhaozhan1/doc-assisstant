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


class TestPdfExtract:
    def test_extracts_pdf_with_text(self, extractor: Extractor, tmp_path: Path) -> None:
        """PDF with a text layer should extract text via pdfplumber."""
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            b"4 0 obj << /Length 82 >> stream\n"
            b"BT /F1 12 Tf 100 700 Td (This is a PDF with enough text to pass threshold) Tj ET\n"
            b"endstream endobj\n"
            b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n"
            b"trailer << /Size 6 /Root 1 0 R >>\n"
            b"startxref 0\n%%EOF"
        )
        pdf_path = tmp_path / "test_with_text.pdf"
        pdf_path.write_bytes(pdf_bytes)
        fi = FileInfo(path=pdf_path, format=".pdf")
        doc = extractor.extract(fi)
        assert "enough text" in doc.text
        assert doc.source_path == pdf_path


class TestTxtGb18030:
    def test_extracts_txt_gb18030_encoding(self, extractor: Extractor, tmp_path: Path) -> None:
        """TXT file encoded in GB18030 should be decoded via the fallback path."""
        content = "这是一段GB18030编码的中文文本"
        txt_path = tmp_path / "gb18030.txt"
        txt_path.write_bytes(content.encode("gb18030"))
        fi = FileInfo(path=txt_path, format=".txt")
        doc = extractor.extract(fi)
        assert "GB18030" in doc.text
        assert "中文文本" in doc.text


class TestXlsxMultiSheet:
    def test_extracts_xlsx_multi_sheet(self, extractor: Extractor, tmp_path: Path) -> None:
        """XLSX with 2+ sheets should extract text from all sheets."""
        from openpyxl import Workbook

        wb = Workbook()
        ws1 = wb.active
        ws1.title = "Sheet1"
        ws1.append(["姓名", "部门"])
        ws1.append(["张三", "技术部"])

        ws2 = wb.create_sheet("Sheet2")
        ws2.append(["项目", "状态"])
        ws2.append(["公文系统", "已完成"])

        xlsx_path = tmp_path / "multi_sheet.xlsx"
        wb.save(str(xlsx_path))
        wb.close()

        fi = FileInfo(path=xlsx_path, format=".xlsx")
        doc = extractor.extract(fi)
        assert "张三" in doc.text
        assert "技术部" in doc.text
        assert "公文系统" in doc.text
        assert "已完成" in doc.text


class TestEmptyFile:
    def test_handles_empty_txt(self, extractor: Extractor, tmp_path: Path) -> None:
        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")
        fi = FileInfo(path=empty, format=".txt")
        doc = extractor.extract(fi)
        assert doc.text == ""
