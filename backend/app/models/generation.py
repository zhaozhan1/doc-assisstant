from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.search import SourceType, UnifiedSearchResult


class ParsedIntent(BaseModel):
    doc_type: str
    topic: str
    keywords: list[str] = Field(default_factory=list)
    raw_input: str


class TemplateSection(BaseModel):
    title: str
    writing_points: list[str] = Field(default_factory=list)
    format_rules: list[str] = Field(default_factory=list)


class TemplateDef(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    name: str
    doc_type: str
    sections: list[TemplateSection] = Field(default_factory=list)
    is_builtin: bool = True


class PromptContext(BaseModel):
    intent: ParsedIntent
    style_refs: list[UnifiedSearchResult] = Field(default_factory=list)
    policy_refs: list[UnifiedSearchResult] = Field(default_factory=list)
    template: TemplateDef | None = None


class SourceAttribution(BaseModel):
    title: str
    source_type: SourceType
    url: str | None = None
    date: str | None = None


class GenerationRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    selected_refs: list[str] | None = None
    requirements: str | None = None
    template_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]+$")


class GenerationResult(BaseModel):
    content: str
    sources: list[SourceAttribution] = Field(default_factory=list)
    output_path: str | None = None
    template_used: str
