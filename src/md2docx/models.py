from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class ParagraphBlock:
    text: str


@dataclass
class ListBlock:
    items: list[str]
    ordered: bool = False


@dataclass
class CodeBlock:
    code: str
    lang: str = ""


@dataclass
class MermaidBlock:
    code: str


BlockNode = ParagraphBlock | ListBlock | CodeBlock | MermaidBlock


@dataclass
class SectionNode:
    level: int
    title_raw: str
    title_norm: str
    path_norm: str
    blocks: list[BlockNode] = field(default_factory=list)
    children: list["SectionNode"] = field(default_factory=list)


@dataclass
class DocumentNode:
    sections: list[SectionNode]


@dataclass
class TemplateHeading:
    paragraph_index: int
    level: int
    title_raw: str
    title_norm: str
    path_norm: str
    style_name: str


@dataclass
class MatchResult:
    md_path: str
    md_title: str
    strategy: Literal["path_exact", "text_exact", "text_fuzzy", "unmatched", "ambiguous"]
    confidence: float
    template_paragraph_index: int | None = None
    template_path: str | None = None
    issue_code: str | None = None
    candidate_paths: list[str] = field(default_factory=list)
    candidate_paragraph_indices: list[int] = field(default_factory=list)
    warning: str | None = None


@dataclass
class MatchConfig:
    use_path: bool = True
    fuzzy_threshold: float = 0.88
    duplicate_policy: Literal["first", "error", "by_level"] = "error"


@dataclass
class MermaidConfig:
    enabled: bool = True
    mmdc_path: str = "mmdc"
    puppeteer_config: str | None = None
    output_format: Literal["png", "svg"] = "png"
    width: int = 1600
    timeout_sec: int = 20
    on_error: Literal["keep_code", "placeholder", "raise"] = "keep_code"
    image_width_ratio: float = 0.8


@dataclass
class InsertConfig:
    mode: Literal["replace", "append"] = "replace"
    list_fallback_prefix: str = "-"
    code_font_name: str = "Consolas"


@dataclass
class ReportConfig:
    path: Path | None = None


@dataclass
class ConvertConfig:
    input: Path
    template: Path
    output: Path
    match: MatchConfig = field(default_factory=MatchConfig)
    insert: InsertConfig = field(default_factory=InsertConfig)
    mermaid: MermaidConfig = field(default_factory=MermaidConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    strict: bool = False


@dataclass
class MermaidRenderResult:
    ok: bool
    image_path: Path | None = None
    error: str | None = None


@dataclass
class ConversionReport:
    matched: list[MatchResult] = field(default_factory=list)
    ambiguous: list[MatchResult] = field(default_factory=list)
    unmatched: list[MatchResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mermaid_failures: list[str] = field(default_factory=list)
