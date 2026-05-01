from __future__ import annotations

import logging
from pathlib import Path

import yaml

from app.models.generation import TemplateDef

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages built-in and custom document templates."""

    def __init__(self, builtin_dir: Path, custom_dir: Path) -> None:
        self._builtin_dir = builtin_dir
        self._custom_dir = custom_dir
        self._custom_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self, doc_type: str | None = None) -> list[TemplateDef]:
        results = []
        for tmpl in self._load_builtin():
            if doc_type is None or tmpl.doc_type == doc_type:
                results.append(tmpl)
        for tmpl in self._load_custom():
            if doc_type is None or tmpl.doc_type == doc_type:
                results.append(tmpl)
        return results

    def get_template(self, template_id: str) -> TemplateDef:
        for tmpl in self._load_builtin():
            if tmpl.id == template_id:
                return tmpl
        for tmpl in self._load_custom():
            if tmpl.id == template_id:
                return tmpl
        raise FileNotFoundError(f"模板不存在: {template_id}")

    def create_template(self, template: TemplateDef) -> TemplateDef:
        template.is_builtin = False
        path = self._custom_dir / f"{template.id}.yaml"
        if path.exists():
            raise FileExistsError(f"模板已存在: {template.id}")
        path.write_text(
            yaml.dump(
                template.model_dump(exclude={"is_builtin"}),
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        return template

    def update_template(self, template_id: str, data: TemplateDef) -> TemplateDef:
        existing = self.get_template(template_id)
        if existing.is_builtin:
            raise PermissionError(f"内置模板不可修改: {template_id}")
        path = self._custom_dir / f"{template_id}.yaml"
        data.is_builtin = False
        path.write_text(
            yaml.dump(
                data.model_dump(exclude={"is_builtin"}),
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        return data

    def delete_template(self, template_id: str) -> None:
        existing = self.get_template(template_id)
        if existing.is_builtin:
            raise PermissionError(f"内置模板不可删除: {template_id}")
        path = self._custom_dir / f"{template_id}.yaml"
        path.unlink()

    def _load_builtin(self) -> list[TemplateDef]:
        results = []
        if not self._builtin_dir.exists():
            return results
        for f in sorted(self._builtin_dir.glob("*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            data["is_builtin"] = True
            results.append(TemplateDef.model_validate(data))
        return results

    def _load_custom(self) -> list[TemplateDef]:
        results = []
        for f in sorted(self._custom_dir.glob("*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            data["is_builtin"] = False
            results.append(TemplateDef.model_validate(data))
        return results
