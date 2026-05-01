from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

logger = logging.getLogger(__name__)

FONT_CANDIDATES = {
    "title": ("方正小标宋简体", "宋体"),
    "heading1": ("方正黑体_GBK", "黑体"),
    "heading2": ("方正楷体_GBK", "楷体"),
    "heading3": ("方正仿宋_GBK", "仿宋"),
    "body": ("方正仿宋_GBK", "仿宋"),
}

FONT_SIZES = {
    "title": Pt(22),
    "heading1": Pt(16),
    "heading2": Pt(16),
    "heading3": Pt(16),
    "body": Pt(16),
}

ALIGNMENTS = {
    "title": WD_ALIGN_PARAGRAPH.CENTER,
    "heading1": WD_ALIGN_PARAGRAPH.LEFT,
    "heading2": WD_ALIGN_PARAGRAPH.LEFT,
    "heading3": WD_ALIGN_PARAGRAPH.LEFT,
    "body": WD_ALIGN_PARAGRAPH.LEFT,
}

EN_NUM_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class DocxFormatter:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._font_map = self._detect_fonts()

    def format(self, content: str, doc_type: str, topic: str) -> Path:
        structure = self._parse_structure(content)
        doc = Document()

        for section in doc.sections:
            section.top_margin = Cm(3.7)
            section.bottom_margin = Cm(3.5)
            section.left_margin = Cm(2.8)
            section.right_margin = Cm(2.6)

        for item in structure:
            style_type = item["type"]
            text = item["text"]
            font_name = self._font_map.get(style_type, self._font_map["body"])
            font_size = FONT_SIZES.get(style_type, FONT_SIZES["body"])
            alignment = ALIGNMENTS.get(style_type, ALIGNMENTS["body"])

            p = doc.add_paragraph()
            p.alignment = alignment
            pf = p.paragraph_format
            pf.line_spacing = Pt(28)
            pf.space_before = Pt(0)
            pf.space_after = Pt(0)
            if style_type != "title":
                pf.first_line_indent = Pt(32)

            self._add_text_with_font(p, text, font_name, font_size)

        filename = self._make_filename(doc_type, topic)
        path = self._output_dir / filename
        doc.save(str(path))
        return path

    def _parse_structure(self, content: str) -> list[dict]:
        structure = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("# ") and not line.startswith("## "):
                structure.append({"type": "title", "text": line[2:]})
            elif line.startswith("## "):
                structure.append({"type": "heading1", "text": line[3:]})
            elif line.startswith("### "):
                structure.append({"type": "heading3", "text": line[4:]})
            else:
                structure.append({"type": "body", "text": line})
        return structure

    def _add_text_with_font(self, paragraph, text: str, font_name: str, font_size) -> None:
        parts = EN_NUM_PATTERN.split(text)
        en_parts = EN_NUM_PATTERN.findall(text)
        for i, run_text in enumerate(parts):
            if run_text:
                run = paragraph.add_run(run_text)
                run.font.name = font_name
                run.font.size = font_size
            if i < len(en_parts):
                run = paragraph.add_run(en_parts[i])
                run.font.name = "Times New Roman"
                run.font.size = font_size

    def _make_filename(self, doc_type: str, topic: str) -> str:
        safe_doc_type = re.sub(r"[^\w]", "", doc_type)[:20]
        safe_topic = re.sub(r"[^\w\u4e00-\u9fff]", "", topic)[:20]
        return f"{safe_doc_type}_{safe_topic}_{date.today().isoformat()}.docx"

    def _detect_fonts(self) -> dict:
        available = set()
        from platform import system

        if system() == "Darwin":
            import subprocess

            try:
                result = subprocess.run(
                    ["system_profiler", "SPFontsDataType"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                for names in FONT_CANDIDATES.values():
                    for n in names:
                        if n in result.stdout:
                            available.add(n)
            except Exception:
                pass

        resolved = {}
        for key, (preferred, fallback) in FONT_CANDIDATES.items():
            if preferred in available:
                resolved[key] = preferred
            else:
                resolved[key] = fallback
                if preferred != fallback:
                    logger.info("字体 %s 不可用，降级为 %s", preferred, fallback)
        return resolved
