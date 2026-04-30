from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.ingestion.classifier import Classifier, MetadataExtractor
from app.models.document import ExtractedDoc


@pytest.fixture
def mock_llm() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def classifier(mock_llm: AsyncMock) -> Classifier:
    return Classifier(mock_llm)


@pytest.fixture
def metadata_extractor() -> MetadataExtractor:
    return MetadataExtractor()


class TestClassifier:
    @pytest.mark.asyncio
    async def test_classify_returns_valid_label(self, classifier: Classifier, mock_llm: AsyncMock) -> None:
        mock_llm.classify.return_value = "通知"
        result = await classifier.classify("关于召开会议的通知")
        assert result == "通知"
        mock_llm.classify.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_truncates_long_text(self, classifier: Classifier, mock_llm: AsyncMock) -> None:
        mock_llm.classify.return_value = "报告"
        long_text = "x" * 1000
        await classifier.classify(long_text)
        call_args = mock_llm.classify.call_args
        assert len(call_args[0][0]) <= 500

    @pytest.mark.asyncio
    async def test_classify_fallback_on_unknown_label(self, classifier: Classifier, mock_llm: AsyncMock) -> None:
        mock_llm.classify.return_value = "不存在的类型"
        result = await classifier.classify("随便什么文本")
        assert result == "其他"


class TestMetadataExtractor:
    def test_extracts_date_from_text(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("根据2024年3月15日的工作安排", encoding="utf-8")
        doc = ExtractedDoc(
            text="根据2024年3月15日的工作安排",
            structure=[],
            source_path=f,
        )
        meta = metadata_extractor.extract(doc)
        assert meta.doc_date is not None
        assert meta.doc_date.year == 2024
        assert meta.doc_date.month == 3
        assert meta.doc_date.day == 15

    def test_extracts_date_from_filename(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "20240315-通知.txt"
        f.write_text("无日期文本", encoding="utf-8")
        doc = ExtractedDoc(text="无日期文本", structure=[], source_path=f)
        meta = metadata_extractor.extract(doc)
        assert meta.doc_date is not None
        assert meta.doc_date.year == 2024

    def test_no_date_returns_none(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("没有日期信息", encoding="utf-8")
        doc = ExtractedDoc(text="没有日期信息", structure=[], source_path=f)
        meta = metadata_extractor.extract(doc)
        assert meta.doc_date is None

    def test_computes_md5(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("固定内容", encoding="utf-8")
        doc = ExtractedDoc(text="固定内容", structure=[], source_path=f)
        meta = metadata_extractor.extract(doc)
        assert len(meta.file_md5) == 32

    def test_doc_type_initially_empty(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("test", encoding="utf-8")
        doc = ExtractedDoc(text="test", structure=[], source_path=f)
        meta = metadata_extractor.extract(doc)
        assert meta.doc_type == ""

    def test_import_time_is_datetime(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("test", encoding="utf-8")
        doc = ExtractedDoc(text="test", structure=[], source_path=f)
        meta = metadata_extractor.extract(doc)
        assert isinstance(meta.import_time, datetime)
