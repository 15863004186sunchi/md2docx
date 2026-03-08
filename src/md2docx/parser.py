from __future__ import annotations

from markdown_it import MarkdownIt

from .models import (
    CodeBlock,
    DocumentNode,
    ListBlock,
    MermaidBlock,
    ParagraphBlock,
    SectionNode,
)
from .normalize import normalize_heading


def parse_markdown(markdown_text: str) -> DocumentNode:
    md = MarkdownIt("commonmark")
    tokens = md.parse(markdown_text)
    sections: list[SectionNode] = []
    stack: list[SectionNode] = []

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            level = int(token.tag[1])
            title = ""
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                title = tokens[i + 1].content.strip()
            section = _open_section(level=level, title=title, stack=stack, roots=sections)
            stack.append(section)
            i += 3
            continue

        if not stack:
            i += 1
            continue

        current = stack[-1]
        if token.type == "paragraph_open":
            text = ""
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                text = tokens[i + 1].content.strip()
            if text:
                current.blocks.append(ParagraphBlock(text=text))
            i += 3
            continue

        if token.type in ("bullet_list_open", "ordered_list_open"):
            items, next_index = _consume_list(tokens, i)
            if items:
                current.blocks.append(ListBlock(items=items, ordered=token.type.startswith("ordered")))
            i = next_index
            continue

        if token.type == "fence":
            lang = (token.info or "").strip().split(" ")[0].lower()
            code = token.content.rstrip()
            if lang == "mermaid":
                current.blocks.append(MermaidBlock(code=code))
            else:
                current.blocks.append(CodeBlock(code=code, lang=lang))
            i += 1
            continue

        i += 1

    return DocumentNode(sections=sections)


def _open_section(level: int, title: str, stack: list[SectionNode], roots: list[SectionNode]) -> SectionNode:
    while stack and stack[-1].level >= level:
        stack.pop()
    parent_path = stack[-1].path_norm if stack else ""
    title_norm = normalize_heading(title)
    path_norm = f"{parent_path}/{title_norm}".strip("/")
    node = SectionNode(level=level, title_raw=title, title_norm=title_norm, path_norm=path_norm)
    if stack:
        stack[-1].children.append(node)
    else:
        roots.append(node)
    return node


def _consume_list(tokens, start: int) -> tuple[list[str], int]:
    items: list[str] = []
    depth = 1
    i = start + 1
    while i < len(tokens) and depth > 0:
        token = tokens[i]
        if token.type.endswith("_list_open"):
            depth += 1
        elif token.type.endswith("_list_close"):
            depth -= 1
        elif token.type == "inline" and i > 0 and tokens[i - 1].type == "paragraph_open":
            text = token.content.strip()
            if text:
                items.append(text)
        i += 1
    return items, i

