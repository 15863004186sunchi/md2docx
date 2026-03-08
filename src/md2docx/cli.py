from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
import yaml

from .converter import convert_markdown_to_docx
from .models import ConvertConfig, InsertConfig, MatchConfig, MermaidConfig, ReportConfig

app = typer.Typer(help="Convert Markdown into a Word template by heading mapping.")


@app.callback()
def main() -> None:
    return None


@app.command("convert")
def convert(
    input_md: Path = typer.Option(..., "--input", "-i", help="Input markdown file."),
    template_docx: Path = typer.Option(..., "--template", "-t", help="Template docx file."),
    output_docx: Path = typer.Option(..., "--output", "-o", help="Output docx file."),
    config_file: Path | None = typer.Option(None, "--config", "-c", help="Optional YAML config."),
    report_file: Path | None = typer.Option(None, "--report", "-r", help="Optional report JSON path."),
    strict: bool = typer.Option(False, "--strict", help="Fail when unmatched headings exist."),
    skip_mermaid: bool = typer.Option(False, "--skip-mermaid", help="Disable Mermaid rendering."),
    mermaid_timeout: int | None = typer.Option(None, "--mermaid-timeout", help="Mermaid timeout seconds."),
) -> None:
    try:
        file_cfg = _load_config(config_file)
        cfg = _build_convert_config(
            cli_input=input_md,
            cli_template=template_docx,
            cli_output=output_docx,
            cli_report=report_file,
            strict=strict,
            skip_mermaid=skip_mermaid,
            mermaid_timeout=mermaid_timeout,
            raw=file_cfg,
        )
        report = convert_markdown_to_docx(cfg)
    except Exception as exc:
        typer.secho(f"Conversion failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    typer.secho("Conversion completed.", fg=typer.colors.GREEN)
    typer.echo(f"- matched sections: {len(report.matched)}")
    typer.echo(f"- ambiguous sections: {len(report.ambiguous)}")
    typer.echo(f"- unmatched sections: {len(report.unmatched)}")
    typer.echo(f"- mermaid failures: {len(report.mermaid_failures)}")
    if cfg.report.path:
        typer.echo(f"- report file: {cfg.report.path}")


def _load_config(config_file: Path | None) -> dict[str, Any]:
    if config_file is None:
        return {}
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    with config_file.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, dict):
        raise ValueError("Config YAML root must be an object")
    return data


def _build_convert_config(
    cli_input: Path,
    cli_template: Path,
    cli_output: Path,
    cli_report: Path | None,
    strict: bool,
    skip_mermaid: bool,
    mermaid_timeout: int | None,
    raw: dict[str, Any],
) -> ConvertConfig:
    match_raw = raw.get("match", {})
    insert_raw = raw.get("insert", {})
    mermaid_raw = raw.get("mermaid", {})
    report_raw = raw.get("report", {})
    duplicate_policy = str(match_raw.get("duplicate_policy", "error"))
    if duplicate_policy not in {"first", "error", "by_level"}:
        raise ValueError("match.duplicate_policy must be one of: first, error, by_level")

    match_cfg = MatchConfig(
        use_path=bool(match_raw.get("use_path", True)),
        fuzzy_threshold=float(match_raw.get("fuzzy_threshold", 0.88)),
        duplicate_policy=duplicate_policy,  # type: ignore[arg-type]
    )
    insert_cfg = InsertConfig(
        mode=str(insert_raw.get("mode", "replace")),
        list_fallback_prefix=str(insert_raw.get("list_fallback_prefix", "-")),
        code_font_name=str(insert_raw.get("code_font_name", "Consolas")),
    )
    mermaid_cfg = MermaidConfig(
        enabled=bool(mermaid_raw.get("enabled", True)),
        mmdc_path=str(mermaid_raw.get("mmdc_path", "mmdc")),
        puppeteer_config=(str(mermaid_raw["puppeteer_config"]) if "puppeteer_config" in mermaid_raw else None),
        output_format=str(mermaid_raw.get("output_format", "png")),
        width=int(mermaid_raw.get("width", 1600)),
        timeout_sec=int(mermaid_raw.get("timeout_sec", 20)),
        on_error=str(mermaid_raw.get("on_error", "keep_code")),
        image_width_ratio=float(mermaid_raw.get("image_width_ratio", 0.8)),
    )
    if skip_mermaid:
        mermaid_cfg.enabled = False
    if mermaid_timeout is not None:
        mermaid_cfg.timeout_sec = mermaid_timeout

    report_path = cli_report
    if report_path is None and isinstance(report_raw, dict):
        raw_path = report_raw.get("path")
        if raw_path:
            report_path = Path(str(raw_path))
    report_cfg = ReportConfig(path=report_path)

    return ConvertConfig(
        input=cli_input,
        template=cli_template,
        output=cli_output,
        match=match_cfg,
        insert=insert_cfg,
        mermaid=mermaid_cfg,
        report=report_cfg,
        strict=strict,
    )
