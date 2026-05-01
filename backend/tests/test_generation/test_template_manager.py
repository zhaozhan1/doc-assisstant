from __future__ import annotations

from pathlib import Path

import pytest

from app.generation.template_manager import TemplateManager
from app.models.generation import TemplateDef

BUILTIN_IDS = [
    "notice",
    "announcement",
    "request",
    "report",
    "plan",
    "program",
    "minutes",
    "contract",
    "work_summary",
    "speech",
    "research_report",
    "presentation",
]


@pytest.fixture
def builtin_dir() -> Path:
    return Path(__file__).parent.parent.parent / "app" / "generation" / "templates"


@pytest.fixture
def tm(tmp_path: Path, builtin_dir: Path) -> TemplateManager:
    return TemplateManager(builtin_dir=builtin_dir, custom_dir=tmp_path / "custom")


class TestBuiltinTemplates:
    def test_list_all_builtins(self, tm: TemplateManager):
        templates = tm.list_templates()
        builtin = [t for t in templates if t.is_builtin]
        assert len(builtin) == 12
        assert {t.id for t in builtin} == set(BUILTIN_IDS)

    def test_get_builtin_by_id(self, tm: TemplateManager):
        t = tm.get_template("notice")
        assert t.name == "通知"
        assert t.is_builtin is True
        assert len(t.sections) > 0

    def test_filter_by_doc_type(self, tm: TemplateManager):
        results = tm.list_templates(doc_type="notice")
        assert all(t.doc_type == "notice" for t in results)
        assert len(results) >= 1

    def test_get_nonexistent_raises(self, tm: TemplateManager):
        with pytest.raises(FileNotFoundError):
            tm.get_template("nonexistent_template")


class TestCustomTemplates:
    def test_create_custom_template(self, tm: TemplateManager):
        new_tmpl = TemplateDef(
            id="custom_test",
            name="自定义测试模板",
            doc_type="notice",
            sections=[
                {
                    "title": "测试段",
                    "writing_points": ["要点1"],
                    "format_rules": [],
                }
            ],
            is_builtin=False,
        )
        result = tm.create_template(new_tmpl)
        assert result.id == "custom_test"
        assert result.is_builtin is False

    def test_list_includes_custom(self, tm: TemplateManager):
        new_tmpl = TemplateDef(
            id="custom_extra",
            name="额外模板",
            doc_type="report",
            is_builtin=False,
        )
        tm.create_template(new_tmpl)
        all_tmpls = tm.list_templates()
        ids = [t.id for t in all_tmpls]
        assert "custom_extra" in ids

    def test_update_custom_template(self, tm: TemplateManager):
        new_tmpl = TemplateDef(
            id="custom_to_update",
            name="原始名称",
            doc_type="notice",
            is_builtin=False,
        )
        tm.create_template(new_tmpl)
        updated = TemplateDef(
            id="custom_to_update",
            name="更新名称",
            doc_type="notice",
            is_builtin=False,
        )
        result = tm.update_template("custom_to_update", updated)
        assert result.name == "更新名称"

    def test_delete_custom_template(self, tm: TemplateManager):
        new_tmpl = TemplateDef(
            id="custom_to_delete",
            name="待删除",
            doc_type="notice",
            is_builtin=False,
        )
        tm.create_template(new_tmpl)
        tm.delete_template("custom_to_delete")
        with pytest.raises(FileNotFoundError):
            tm.get_template("custom_to_delete")

    def test_update_builtin_raises(self, tm: TemplateManager):
        with pytest.raises(PermissionError):
            tm.update_template("notice", tm.get_template("notice"))

    def test_delete_builtin_raises(self, tm: TemplateManager):
        with pytest.raises(PermissionError):
            tm.delete_template("notice")

    def test_create_duplicate_raises(self, tm: TemplateManager):
        new_tmpl = TemplateDef(
            id="custom_dup",
            name="重复模板",
            doc_type="notice",
            is_builtin=False,
        )
        tm.create_template(new_tmpl)
        with pytest.raises(FileExistsError):
            tm.create_template(new_tmpl)
