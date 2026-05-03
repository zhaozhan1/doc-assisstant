from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from app.generation.docx_formatter import DocxFormatter
from app.generation.intent_parser import IntentParser
from app.generation.prompt_builder import PromptBuilder
from app.generation.template_manager import TemplateManager
from app.generation.writer import Writer
from app.models.generation import GenerationRequest, GenerationResult, PromptContext, SourceAttribution
from app.models.search import SearchRequest, SourceType
from app.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)


class WriterService:
    def __init__(
        self,
        intent_parser: IntentParser,
        prompt_builder: PromptBuilder,
        template_mgr: TemplateManager,
        writer: Writer,
        docx_formatter: DocxFormatter,
        retriever: Retriever,
    ) -> None:
        self._intent_parser = intent_parser
        self._prompt_builder = prompt_builder
        self._template_mgr = template_mgr
        self._writer = writer
        self._docx_formatter = docx_formatter
        self._retriever = retriever

    async def generate_from_description(self, req: GenerationRequest) -> GenerationResult:
        intent = await self._intent_parser.parse(req.description)
        template = self._resolve_template(req.template_id, intent.doc_type)
        search_results = await self._retriever.search(SearchRequest(query=" ".join(intent.keywords), top_k=5))
        context = PromptContext(
            intent=intent,
            style_refs=[r for r in search_results[:5] if r.source_type == SourceType.LOCAL],
            policy_refs=[r for r in search_results if r.source_type == SourceType.ONLINE],
            template=template,
        )
        messages = self._prompt_builder.build(context)
        content = await self._writer.generate(messages)
        output_path = self._docx_formatter.format(content, intent.doc_type, intent.topic)
        sources = self._extract_sources(search_results)

        return GenerationResult(
            content=content,
            sources=sources,
            output_path=str(output_path),
            template_used=template.id,
        )

    async def generate_from_selection(self, req: GenerationRequest) -> GenerationResult:
        intent = await self._intent_parser.parse(req.requirements or req.description)
        template = self._resolve_template(req.template_id, intent.doc_type)
        style_refs = await self._fetch_selected_refs(req.selected_refs or [])
        context = PromptContext(
            intent=intent,
            style_refs=style_refs,
            policy_refs=[],
            template=template,
        )
        messages = self._prompt_builder.build(context)
        content = await self._writer.generate(messages)
        output_path = self._docx_formatter.format(content, intent.doc_type, intent.topic)
        sources = self._extract_sources(style_refs)

        return GenerationResult(
            content=content,
            sources=sources,
            output_path=str(output_path),
            template_used=template.id,
        )

    async def generate_stream(self, req: GenerationRequest) -> AsyncGenerator[str, None]:
        intent = await self._intent_parser.parse(req.description)
        template = self._resolve_template(req.template_id, intent.doc_type)
        search_results = await self._retriever.search(SearchRequest(query=" ".join(intent.keywords), top_k=5))
        context = PromptContext(
            intent=intent,
            style_refs=[r for r in search_results[:5] if r.source_type == SourceType.LOCAL],
            policy_refs=[r for r in search_results if r.source_type == SourceType.ONLINE],
            template=template,
        )
        messages = self._prompt_builder.build(context)
        async for token in self._writer.generate_stream(messages):
            yield token

    def _resolve_template(self, template_id: str | None, doc_type: str):
        if template_id:
            try:
                return self._template_mgr.get_template(template_id)
            except FileNotFoundError:
                pass
        templates = self._template_mgr.list_templates(doc_type=doc_type)
        if templates:
            return templates[0]
        templates = self._template_mgr.list_templates(doc_type="report")
        if templates:
            return templates[0]
        all_templates = self._template_mgr.list_templates()
        if all_templates:
            return all_templates[0]
        raise FileNotFoundError("没有可用的公文模板")

    async def _fetch_selected_refs(self, ref_ids: list[str]) -> list:
        if not ref_ids:
            return []
        return await self._retriever.search(SearchRequest(query=" ".join(ref_ids), top_k=len(ref_ids)))

    async def save_stream_result(self, content: str, description: str) -> str:
        intent = await self._intent_parser.parse(description)
        output_path = self._docx_formatter.format(content, intent.doc_type, intent.topic)
        return str(output_path)

    def _extract_sources(self, results: list) -> list[SourceAttribution]:
        sources = []
        for r in results:
            sources.append(
                SourceAttribution(
                    title=r.title,
                    source_type=r.source_type,
                    url=r.metadata.get("url"),
                    date=r.metadata.get("doc_date"),
                )
            )
        return sources
