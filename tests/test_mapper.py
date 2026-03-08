from md2docx.mapper import map_sections
from md2docx.models import DocumentNode, MatchConfig, SectionNode, TemplateHeading


def test_duplicate_policy_first_picks_first_candidate() -> None:
    document = DocumentNode(
        sections=[SectionNode(level=2, title_raw="接口设计", title_norm="接口设计", path_norm="总体/接口设计")]
    )
    headings = [
        TemplateHeading(
            paragraph_index=10,
            level=2,
            title_raw="接口设计",
            title_norm="接口设计",
            path_norm="总体/接口设计",
            style_name="Heading 2",
        ),
        TemplateHeading(
            paragraph_index=20,
            level=2,
            title_raw="接口设计",
            title_norm="接口设计",
            path_norm="总体/接口设计",
            style_name="Heading 2",
        ),
    ]
    result = map_sections(document, headings, MatchConfig(duplicate_policy="first"))[0]
    assert result.template_paragraph_index == 10
    assert result.strategy == "path_exact"


def test_duplicate_policy_error_marks_ambiguous_with_candidates() -> None:
    document = DocumentNode(
        sections=[SectionNode(level=2, title_raw="接口设计", title_norm="接口设计", path_norm="总体/接口设计")]
    )
    headings = [
        TemplateHeading(
            paragraph_index=10,
            level=2,
            title_raw="接口设计",
            title_norm="接口设计",
            path_norm="总体/接口设计",
            style_name="Heading 2",
        ),
        TemplateHeading(
            paragraph_index=20,
            level=2,
            title_raw="接口设计",
            title_norm="接口设计",
            path_norm="总体/接口设计",
            style_name="Heading 2",
        ),
    ]
    result = map_sections(document, headings, MatchConfig(duplicate_policy="error"))[0]
    assert result.template_paragraph_index is None
    assert result.strategy == "ambiguous"
    assert result.issue_code == "E3001"
    assert result.candidate_paragraph_indices == [10, 20]


def test_duplicate_policy_by_level_uses_unique_level_match() -> None:
    document = DocumentNode(
        sections=[SectionNode(level=3, title_raw="方案", title_norm="方案", path_norm="总体/方案")]
    )
    headings = [
        TemplateHeading(
            paragraph_index=10,
            level=2,
            title_raw="方案",
            title_norm="方案",
            path_norm="一级/方案",
            style_name="Heading 2",
        ),
        TemplateHeading(
            paragraph_index=20,
            level=3,
            title_raw="方案",
            title_norm="方案",
            path_norm="二级/方案",
            style_name="Heading 3",
        ),
    ]
    result = map_sections(document, headings, MatchConfig(use_path=False, duplicate_policy="by_level"))[0]
    assert result.template_paragraph_index == 20
    assert result.strategy == "text_exact"

