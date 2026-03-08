import pytest


def test_parser_builds_sections_and_mermaid() -> None:
    pytest.importorskip("markdown_it")
    from md2docx.models import MermaidBlock
    from md2docx.parser import parse_markdown

    content = """# 概述

文本A

## 流程
```mermaid
flowchart TD
  A-->B
```
"""
    doc = parse_markdown(content)
    assert len(doc.sections) == 1
    assert doc.sections[0].title_norm == "概述"
    assert doc.sections[0].children[0].title_norm == "流程"
    assert any(isinstance(block, MermaidBlock) for block in doc.sections[0].children[0].blocks)
