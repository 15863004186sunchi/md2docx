from __future__ import annotations

import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from .converter import convert_markdown_to_docx
from .models import ConvertConfig, InsertConfig, MatchConfig, MermaidConfig, ReportConfig

app = FastAPI(title="md2docx Web", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>md2docx Web</title>
  <style>
    body{font-family:Arial,sans-serif;max-width:840px;margin:40px auto;padding:0 12px}
    .card{border:1px solid #ddd;border-radius:8px;padding:18px}
    .row{margin:10px 0}
    label{display:block;font-weight:600;margin-bottom:6px}
    input,select{width:100%;padding:8px}
    button{margin-top:12px;padding:10px 16px}
    .hint{color:#666;font-size:13px}
  </style>
</head>
<body>
  <h2>Markdown 转 Word（Web）</h2>
  <div class="card">
    <form action="/api/convert" method="post" enctype="multipart/form-data">
      <div class="row">
        <label>Markdown 文件（.md）</label>
        <input type="file" name="markdown_file" accept=".md,text/markdown" required />
      </div>
      <div class="row">
        <label>Word 模板（.docx）</label>
        <input type="file" name="template_file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required />
      </div>
      <div class="row">
        <label>duplicate_policy</label>
        <select name="duplicate_policy">
          <option value="error">error</option>
          <option value="by_level">by_level</option>
          <option value="first">first</option>
        </select>
      </div>
      <div class="row">
        <label>strict</label>
        <select name="strict">
          <option value="false">false</option>
          <option value="true">true</option>
        </select>
      </div>
      <div class="row">
        <label>skip_mermaid</label>
        <select name="skip_mermaid">
          <option value="false">false</option>
          <option value="true">true</option>
        </select>
      </div>
      <div class="row">
        <label>mermaid_timeout（秒）</label>
        <input type="number" name="mermaid_timeout" min="1" value="20" />
      </div>
      <button type="submit">开始转换并下载 ZIP</button>
      <p class="hint">输出为 ZIP：包含 result.docx 与 report.json。</p>
    </form>
  </div>
</body>
</html>
"""


@app.post("/api/convert")
async def convert_api(
    markdown_file: UploadFile = File(...),
    template_file: UploadFile = File(...),
    duplicate_policy: str = Form("error"),
    strict: str = Form("false"),
    skip_mermaid: str = Form("false"),
    mermaid_timeout: int = Form(20),
) -> StreamingResponse:
    if duplicate_policy not in {"first", "error", "by_level"}:
        raise HTTPException(status_code=400, detail="duplicate_policy must be first/error/by_level")
    if not markdown_file.filename or not markdown_file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="markdown_file must be .md")
    if not template_file.filename or not template_file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="template_file must be .docx")

    strict_flag = _to_bool(strict)
    skip_mermaid_flag = _to_bool(skip_mermaid)

    with tempfile.TemporaryDirectory(prefix="md2docx-web-") as tmp_dir:
        tmp = Path(tmp_dir)
        markdown_path = tmp / "input.md"
        template_path = tmp / "template.docx"
        output_docx = tmp / "result.docx"
        report_path = tmp / "report.json"

        markdown_path.write_bytes(await markdown_file.read())
        template_path.write_bytes(await template_file.read())

        cfg = ConvertConfig(
            input=markdown_path,
            template=template_path,
            output=output_docx,
            match=MatchConfig(duplicate_policy=duplicate_policy),  # type: ignore[arg-type]
            insert=InsertConfig(),
            mermaid=MermaidConfig(
                enabled=not skip_mermaid_flag,
                timeout_sec=mermaid_timeout,
                puppeteer_config=os.getenv("MD2DOCX_MMDC_PUPPETEER_CONFIG"),
            ),
            report=ReportConfig(path=report_path),
            strict=strict_flag,
        )

        try:
            report = convert_markdown_to_docx(cfg)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        zip_bytes = _build_zip_bytes(output_docx, report_path, report_summary={
            "matched": len(report.matched),
            "ambiguous": len(report.ambiguous),
            "unmatched": len(report.unmatched),
            "mermaid_failures": len(report.mermaid_failures),
        })

    output_name = "md2docx_result.zip"
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{output_name}"'},
    )


def _build_zip_bytes(docx_path: Path, report_path: Path, report_summary: dict[str, int]) -> bytes:
    content = io.BytesIO()
    with zipfile.ZipFile(content, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("result.docx", docx_path.read_bytes())
        zf.writestr("report.json", report_path.read_bytes())
        zf.writestr("summary.json", json.dumps(report_summary, ensure_ascii=False, indent=2))
    content.seek(0)
    return content.getvalue()


def _to_bool(raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}
