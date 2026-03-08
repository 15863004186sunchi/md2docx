from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher

from .models import DocumentNode, MatchConfig, MatchResult, SectionNode, TemplateHeading


def map_sections(document: DocumentNode, headings: list[TemplateHeading], cfg: MatchConfig) -> list[MatchResult]:
    path_map: dict[str, list[TemplateHeading]] = defaultdict(list)
    title_map: dict[str, list[TemplateHeading]] = defaultdict(list)
    for heading in headings:
        path_map[heading.path_norm].append(heading)
        title_map[heading.title_norm].append(heading)

    results: list[MatchResult] = []
    for section in _flatten_sections(document.sections):
        result = _map_one(section, headings, path_map, title_map, cfg)
        results.append(result)
    return results


def _flatten_sections(sections: list[SectionNode]) -> list[SectionNode]:
    flattened: list[SectionNode] = []
    for section in sections:
        flattened.append(section)
        flattened.extend(_flatten_sections(section.children))
    return flattened


def _map_one(
    section: SectionNode,
    headings: list[TemplateHeading],
    path_map: dict[str, list[TemplateHeading]],
    title_map: dict[str, list[TemplateHeading]],
    cfg: MatchConfig,
) -> MatchResult:
    if cfg.use_path and section.path_norm in path_map:
        candidates = path_map[section.path_norm]
        chosen = _pick_candidate(candidates, cfg, section.level)
        if chosen is not None:
            return _matched(section, chosen, "path_exact", 1.0)
        return _ambiguous_result(
            section=section,
            warning=f"Path duplicated in template: {section.path_norm}",
            candidates=candidates,
        )

    if section.title_norm in title_map:
        candidates = title_map[section.title_norm]
        chosen = _pick_candidate(candidates, cfg, section.level)
        if chosen is not None:
            return _matched(section, chosen, "text_exact", 0.95)
        return _ambiguous_result(
            section=section,
            warning=f"Title duplicated in template: {section.title_raw}",
            candidates=candidates,
        )

    fuzzy = _fuzzy_match(section, headings, cfg.fuzzy_threshold)
    if fuzzy:
        return _matched(section, fuzzy, "text_fuzzy", 0.8)

    return MatchResult(
        md_path=section.path_norm,
        md_title=section.title_raw,
        strategy="unmatched",
        confidence=0.0,
        issue_code="E3002",
        warning=f"No matching heading in template for {section.title_raw}",
    )


def _pick_candidate(candidates: list[TemplateHeading], cfg: MatchConfig, section_level: int) -> TemplateHeading | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if cfg.duplicate_policy == "first":
        return candidates[0]
    if cfg.duplicate_policy == "by_level":
        same_level = [candidate for candidate in candidates if candidate.level == section_level]
        if len(same_level) == 1:
            return same_level[0]
    return None


def _fuzzy_match(section: SectionNode, headings: list[TemplateHeading], threshold: float) -> TemplateHeading | None:
    if threshold <= 0:
        return None
    best_score = 0.0
    best_heading: TemplateHeading | None = None
    second_score = 0.0
    for heading in headings:
        score = SequenceMatcher(None, section.title_norm, heading.title_norm).ratio()
        if score > best_score:
            second_score = best_score
            best_score = score
            best_heading = heading
        elif score > second_score:
            second_score = score
    if best_heading is None or best_score < threshold:
        return None
    if (best_score - second_score) < 0.03:
        return None
    return best_heading


def _matched(section: SectionNode, heading: TemplateHeading, strategy: str, confidence: float) -> MatchResult:
    return MatchResult(
        md_path=section.path_norm,
        md_title=section.title_raw,
        strategy=strategy,  # type: ignore[arg-type]
        confidence=confidence,
        template_paragraph_index=heading.paragraph_index,
        template_path=heading.path_norm,
    )


def _ambiguous_result(section: SectionNode, warning: str, candidates: list[TemplateHeading]) -> MatchResult:
    return MatchResult(
        md_path=section.path_norm,
        md_title=section.title_raw,
        strategy="ambiguous",
        confidence=0.0,
        issue_code="E3001",
        candidate_paths=[item.path_norm for item in candidates],
        candidate_paragraph_indices=[item.paragraph_index for item in candidates],
        warning=warning,
    )
