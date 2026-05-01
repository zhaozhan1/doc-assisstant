from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.generation.docx_formatter import DocxFormatter

SAMPLE_CONTENT = """# 关于国庆节放假安排的通知

各科室：

根据国务院办公厅通知精神，现将国庆节放假安排通知如下。

## 一、放假时间

10月1日至10月7日放假调休，共7天。

## 二、有关要求

各部门要妥善安排好值班和安全保卫等工作。

三、注意事项

节假日期间注意出行安全。

XX单位
2024年9月20日
"""


@pytest.fixture
def formatter(tmp_path: Path) -> DocxFormatter:
    return DocxFormatter(output_dir=tmp_path)


class TestDocxFormatter:
    def test_format_creates_docx(self, formatter: DocxFormatter):
        path = formatter.format(SAMPLE_CONTENT, "notice", "国庆节放假")
        assert path.exists()
        assert path.suffix == ".docx"

    def test_file_naming(self, formatter: DocxFormatter):
        path = formatter.format(SAMPLE_CONTENT, "notice", "放假安排")
        name = path.name
        assert name.startswith("notice_")
        assert name.endswith(".docx")
        assert date.today().isoformat() in name

    def test_topic_truncation(self, formatter: DocxFormatter):
        long_topic = "这" * 30
        path = formatter.format(SAMPLE_CONTENT, "report", long_topic)
        name = path.stem
        topic_part = name.split("_")[1]
        assert len(topic_part) <= 20

    def test_font_detection(self, formatter: DocxFormatter):
        font_map = formatter._font_map
        assert "body" in font_map
        assert "title" in font_map
        assert len(font_map) >= 5

    def test_parse_structure(self, formatter: DocxFormatter):
        structure = formatter._parse_structure(SAMPLE_CONTENT)
        assert len(structure) > 0
        types = [s["type"] for s in structure]
        assert "title" in types or "heading1" in types

    def test_empty_content_still_creates_file(self, formatter: DocxFormatter):
        path = formatter.format("简单内容", "report", "测试")
        assert path.exists()
