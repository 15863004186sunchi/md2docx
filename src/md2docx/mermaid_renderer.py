from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

from .models import MermaidConfig, MermaidRenderResult


class MermaidRenderer:
    def __init__(self, cfg: MermaidConfig, work_dir: Path):
        self.cfg = cfg
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def render(self, code: str) -> MermaidRenderResult:
        if not self.cfg.enabled:
            return MermaidRenderResult(ok=False, error="Mermaid rendering disabled")

        digest = hashlib.sha1(code.encode("utf-8")).hexdigest()[:16]
        src_path = self.work_dir / f"{digest}.mmd"
        out_path = self.work_dir / f"{digest}.{self.cfg.output_format}"
        if out_path.exists():
            return MermaidRenderResult(ok=True, image_path=out_path)

        src_path.write_text(code, encoding="utf-8")
        executable = _resolve_mmdc_executable(self.cfg.mmdc_path)
        if executable is None:
            return MermaidRenderResult(ok=False, error=f"mmdc not found: {self.cfg.mmdc_path}")

        command = [
            executable,
            "-i",
            str(src_path),
            "-o",
            str(out_path),
            "-b",
            "transparent",
            "-w",
            str(self.cfg.width),
        ]
        if self.cfg.puppeteer_config:
            command.extend(["-p", self.cfg.puppeteer_config])
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.cfg.timeout_sec,
            )
        except FileNotFoundError:
            return MermaidRenderResult(ok=False, error=f"mmdc not found: {self.cfg.mmdc_path}")
        except subprocess.TimeoutExpired:
            return MermaidRenderResult(ok=False, error="Mermaid render timed out")
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            return MermaidRenderResult(ok=False, error=stderr or "Mermaid render failed")

        return MermaidRenderResult(ok=True, image_path=out_path)


def _resolve_mmdc_executable(raw: str) -> str | None:
    candidates = [raw]
    if sys.platform.startswith("win"):
        lower = raw.lower()
        if not lower.endswith((".cmd", ".exe", ".bat")):
            candidates.extend([f"{raw}.cmd", f"{raw}.exe", f"{raw}.bat"])
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return None
