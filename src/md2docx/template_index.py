from __future__ import annotations

import re

from docx.document import Document as DocxDocument

from .models import TemplateHeading
from .normalize import normalize_heading

_HEADING_LEVEL_RE = re.compile(r"(\d+)")
_HEADING_HINT_RE = re.compile(r"(heading|标题)", re.IGNORECASE)


def build_template_heading_index(doc: DocxDocument) -> list[TemplateHeading]:
    headings: list[TemplateHeading] = []
    path_stack: list[str] = []

    for idx, paragraph in enumerate(doc.paragraphs):
        level = _extract_heading_level(paragraph.style.name if paragraph.style else "")
        if level is None:
            continue
        raw_title = paragraph.text.strip()
        title_norm = normalize_heading(raw_title)
        while len(path_stack) >= level:
            path_stack.pop()
        path_stack.append(title_norm)
        headings.append(
            TemplateHeading(
                paragraph_index=idx,
                level=level,
                title_raw=raw_title,
                title_norm=title_norm,
                path_norm="/".join(path_stack),
                style_name=paragraph.style.name if paragraph.style else "",
            )
        )
    return headings


def _extract_heading_level(style_name: str) -> int | None:
    if not style_name:
        return None
    if not _HEADING_HINT_RE.search(style_name):
        return None
    match = _HEADING_LEVEL_RE.search(style_name)
    if not match:
        return None
    value = int(match.group(1))
    return value if value > 0 else None

