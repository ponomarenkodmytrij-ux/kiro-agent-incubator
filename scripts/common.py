"""Shared helpers for Incubator scripts (stdlib only)."""
from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
POWER = SCRIPTS.parent
LIBRARY = POWER / "steering" / "ui-library.md"
RUNTIME = POWER / "runtime"

META_RE = re.compile(r'<meta name="incubator" content="([^"]*)"')


def parse_kv(path: Path) -> dict[str, str]:
    """Parse a KEY=VALUE file (comments and blank lines ignored)."""
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_env() -> dict[str, str]:
    """Load .env.incubator (INCUBATOR_ENV override, else search upwards from the repo)."""
    override = os.environ.get("INCUBATOR_ENV")
    candidates = [Path(override)] if override else [p / ".env.incubator" for p in SCRIPTS.parents]
    path = next((c for c in candidates if c.is_file()), None)
    if path is None:
        raise SystemExit(
            "⚠️ Файл .env.incubator не знайдено.\n"
            "Скопіюй .env.incubator.example → .env.incubator і заповни свої дані."
        )
    env = parse_kv(path)
    env["_ROOT"] = str(path.parent)
    return env


def output_dir(env: dict[str, str]) -> Path:
    raw = env.get("INCUBATOR_OUTPUT_DIR") or "{workspace}/output"
    return Path(raw.replace("{workspace}", env["_ROOT"])).expanduser()


# ── PDF page target — single source of truth: INCUBATOR_MIN_PDF_PAGES ──
LINES_PER_PDF_PAGE = 42   # measured on weasyprint output of existing templates
MIN_OWN_LINES = 350       # quality floor for style.css + body.html + signature.js
VARIANT_RE = re.compile(r"/\* @variant (\w+):([\w-]+) \*/\n?(.*?)/\* @end \*/\n?", re.S)


def min_pdf_pages(env: dict[str, str]) -> int:
    raw = env.get("INCUBATOR_MIN_PDF_PAGES", "").strip()
    if not raw.isdigit():
        raise SystemExit("⚠️ У .env.incubator немає INCUBATOR_MIN_PDF_PAGES=<число> (мінімум сторінок PDF).")
    return int(raw)


def keep_variants(src: str, chosen: dict[str, str]) -> str:
    """Keep only the chosen @variant blocks of runtime files."""
    return VARIANT_RE.sub(lambda m: m.group(3) if chosen.get(m.group(1)) == m.group(2) else "", src)


def runtime_lines(chosen: dict[str, str]) -> int:
    return sum(keep_variants((RUNTIME / f).read_text(encoding="utf-8"), chosen).count("\n") for f in ("base.css", "core.js"))


def own_lines_target(env: dict[str, str], chosen: dict[str, str]) -> int:
    """Lines the agent should write so the PDF reaches INCUBATOR_MIN_PDF_PAGES (+1 page margin)."""
    need_total = (min_pdf_pages(env) + 1) * LINES_PER_PDF_PAGE
    wrapper = 45  # head, loader, script tags added by build.py
    return max(MIN_OWN_LINES, need_total - runtime_lines(chosen) - wrapper)


def build_dir(env: dict[str, str]) -> Path:
    return output_dir(env) / ".build" / "current"


def read_history(out: Path, limit: int) -> list[dict]:
    """Return metadata of the latest `limit` generated templates (newest first)."""
    history: list[dict] = []
    files = sorted(out.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        m = META_RE.search(f.read_text(encoding="utf-8", errors="ignore")[:6000])
        if not m:
            continue
        try:
            history.append(json.loads(html.unescape(m.group(1))))
        except json.JSONDecodeError:
            continue
        if len(history) >= limit:
            break
    return history
