from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path

from app.llm.base import BaseLLMProvider
from app.models.document import DocumentMetadata, ExtractedDoc

logger = logging.getLogger(__name__)

DOC_TYPES = [
    "通知", "公告", "请示", "报告", "方案", "规划",
    "会议纪要", "合同", "工作总结", "领导讲话稿", "调研报告", "汇报PPT", "其他",
]


class MetadataExtractor:
    _DATE_PATTERNS = [
        (re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"), lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (re.compile(r"(\d{4})(\d{2})(\d{2})"), lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    ]

    def extract(self, doc: ExtractedDoc) -> DocumentMetadata:
        doc_date = self._extract_date(doc.text) or self._extract_date_from_path(doc.source_path)
        file_md5 = self._compute_md5(doc.source_path)
        return DocumentMetadata(
            file_name=doc.source_path.name,
            source_path=str(doc.source_path),
            import_time=datetime.now(),
            doc_date=doc_date,
            doc_type="",
            file_md5=file_md5,
        )

    def _extract_date(self, text: str) -> datetime | None:
        for pattern, constructor in self._DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    return constructor(match)
                except ValueError:
                    continue
        return None

    def _extract_date_from_path(self, path: Path) -> datetime | None:
        name = path.stem
        return self._extract_date(name)

    def _compute_md5(self, path: Path) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()


class Classifier:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    async def classify(self, text: str) -> str:
        result = await self._llm.classify(text[:500], DOC_TYPES)
        if result not in DOC_TYPES:
            return "其他"
        return result
