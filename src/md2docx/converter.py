from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from docx import Document

from .mapper import map_sections
from .mermaid_renderer import MermaidRenderer
from .models import ConversionReport, ConvertConfig, DocumentNode, MatchResult, SectionNode
from .parser import parse_markdown
from .template_index import build_template_heading_index
from .writer import apply_mappings


def convert_markdown_to_docx(config: ConvertConfig) -> ConversionReport:
    _validate_input_paths(config)
    report = ConversionReport()

    markdown_text = config.input.read_text(encoding="utf-8")
    md_doc = parse_markdown(markdown_text)
    sections_by_path = _index_sections_by_path(md_doc)

    doc = Document(str(config.template))
    headings = build_template_heading_index(doc)
    if not headings:
        raise ValueError("No template headings found. Ensure heading styles are available in the template.")

    matches = map_sections(md_doc, headings, config.match)
    report.matched = [item for item in matches if item.template_paragraph_index is not None]
    report.ambiguous = [item for item in matches if item.strategy == "ambiguous"]
    report.unmatched = [item for item in matches if item.strategy == "unmatched"]
    for item in report.ambiguous + report.unmatched:
        if item.warning:
            report.warnings.append(item.warning)

    with tempfile.TemporaryDirectory(prefix="md2docx-mermaid-") as temp_dir:
        renderer = MermaidRenderer(cfg=config.mermaid, work_dir=Path(temp_dir))
        apply_mappings(
            doc=doc,
            sections_by_path=sections_by_path,
            matches=matches,
            headings=headings,
            insert_cfg=config.insert,
            mermaid_renderer=renderer,
            report=report,
            image_ratio=config.mermaid.image_width_ratio,
        )

    config.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(config.output))
    _write_report_if_needed(config.report.path, report)
    _raise_when_strict_needed(config, report)
    return report


def _validate_input_paths(config: ConvertConfig) -> None:
    if not config.input.exists():
        raise FileNotFoundError(f"Markdown file not found: {config.input}")
    if not config.template.exists():
        raise FileNotFoundError(f"Template file not found: {config.template}")


def _index_sections_by_path(md_doc: DocumentNode) -> dict[str, SectionNode]:
    result: dict[str, SectionNode] = {}
    for section in _flatten_sections(md_doc.sections):
        result[section.path_norm] = section
    return result


def _flatten_sections(sections: list[SectionNode]) -> list[SectionNode]:
    flattened: list[SectionNode] = []
    for section in sections:
        flattened.append(section)
        flattened.extend(_flatten_sections(section.children))
    return flattened


def _write_report_if_needed(path: Path | None, report: ConversionReport) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {
        "summary": {
            "matched": len(report.matched),
            "ambiguous": len(report.ambiguous),
            "unmatched": len(report.unmatched),
            "warnings": len(report.warnings),
            "mermaid_failures": len(report.mermaid_failures),
        },
        "matched": [_match_to_dict(item) for item in report.matched],
        "ambiguous": [_match_to_dict(item) for item in report.ambiguous],
        "unmatched": [_match_to_dict(item) for item in report.unmatched],
        "warnings": report.warnings,
        "mermaid_failures": report.mermaid_failures,
    }
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def _match_to_dict(item: MatchResult) -> dict:
    return asdict(item)


def _raise_when_strict_needed(config: ConvertConfig, report: ConversionReport) -> None:
    if not config.strict:
        return
    if report.ambiguous:
        raise ValueError("Strict mode failed: ambiguous heading mappings exist.")
    if report.unmatched:
        raise ValueError("Strict mode failed: unmatched headings exist.")
    if report.mermaid_failures and config.mermaid.on_error == "raise":
        raise ValueError("Strict mode failed: mermaid rendering errors exist.")
