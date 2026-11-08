#!/usr/bin/env python3
"""Incubator build: assemble → validate → PDF → open → documentation → Gmail draft.

Reads <output>/.build/current/{combo.json, style.css, body.html, signature.js},
inlines runtime/base.css + runtime/core.js and writes a single-file template.

Usage:
  build.py --keyword "volt" --concept "VOLT — Field of Live Current" \
           --palette "кислотний лайм і маджента на графіті" \
           --visual "щільної bento-панелі, піксельної типографіки ..." \
           [--template "VOLT"] [--no-draft] [--no-open] [--allow-short] [--check]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

from common import (MIN_OWN_LINES, RUNTIME, build_dir, keep_variants, load_env, min_pdf_pages, output_dir,
                    own_lines_target)

SUPPORTED_ANIMATIONS = {"fade-up", "blur", "scale", "slide-l", "slide-r", "clip-h", "clip-v", "unfold", "rotate",
                        "skew", "flip", "elastic", "morph", "grayscale", "pixel", "draw"}
LOADERS = {
    "counter": '<div><div class="inc-loader__count" data-loader-pct="3">000</div><p class="inc-loader__label">{label}</p></div>',
    "bar": '<div><p class="inc-loader__word">{label}</p><div class="inc-loader__bar"><span data-loader-bar></span></div>'
           '<p class="inc-loader__label"><span data-loader-pct>0</span>%</p></div>',
    "grid": '<div><div class="inc-loader__grid" data-loader-grid></div>'
            '<p class="inc-loader__label">{label} <span data-loader-pct="3">000</span>%</p></div>',
    "curtain": '<span class="inc-loader__half inc-loader__half--a"></span><span class="inc-loader__half inc-loader__half--b"></span>'
               '<p class="inc-loader__word">{label} <span data-loader-pct>0</span></p>',
    "words": '<div><p class="inc-loader__word" data-loader-words="Gathering|Shaping|Revealing|{label}">Gathering</p>'
             '<div class="inc-loader__bar"><span data-loader-bar></span></div></div>',
    "blinds": '<div class="inc-loader__blinds">' + "".join(f'<span style="--i:{i}"></span>' for i in range(8)) + "</div>"
              '<p class="inc-loader__word">{label} <span data-loader-pct>0</span>%</p>',
}
DOC = """Прошу вивести кошти на мій рахунок {account} в {bank} {method}

Артикул роботи: {article}

Призначення коду

Цей код був створений як архітектурний візуальний прототип (Design Showcase). Його головна мета — продемонструвати концепцію «{concept}», де {palette} трансформується у високоестетичний технологічний інтерфейс. Шаблон слугує фундаментом для розробки сайтів преміум-класу, портфоліо креативних студій або імерсивних промо-сторінок, де ключовим фактором є емоційне занурення користувача через складні мікровзаємодії та візуал рівня Awwwards.

Технічний стек та опис

Мова: HTML5, CSS3 (SCSS-style logic), JavaScript (Vanilla ES6+).
Опис: Преміальний односторінковий шаблон "{template}". Візуальна мова базується на поєднанні {visual}.

--
Best regards,
{author}"""
PDF_HEAD = ('<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@page{{size:A4;margin:1cm}}'
            "body{{font-family:Courier New,monospace;font-size:11pt;line-height:1.3}}"
            "h1{{font-family:Arial;font-size:13pt;border-bottom:1px solid #333;padding-bottom:.2cm}}"
            "pre{{white-space:pre-wrap;word-wrap:break-word}}</style></head><body><h1>{title}</h1><pre>")


def unique_path(out: Path, slug: str, stamp: str) -> Path:
    path, n = out / f"{slug}-{stamp}.html", 2
    while path.exists():
        path, n = out / f"{slug}-{stamp}-{n}.html", n + 1
    return path


def node_check(js: str) -> str | None:
    node = shutil.which("node")
    if not node:
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        tmp = Path(f.name)
    try:
        res = subprocess.run([node, "--check", str(tmp)], capture_output=True, text=True)
        return None if res.returncode == 0 else res.stderr.strip().replace(str(tmp), "script")
    finally:
        tmp.unlink(missing_ok=True)


def assemble(work: Path, pick: dict, keyword: str, title: str, description: str, stamp: str) -> tuple[str, str]:
    """Return (full_html, combined_js) for the template."""
    rt = pick["runtime"]
    chosen = {"cursor": rt["cursor"], "preloader": rt["preloader"]}
    base_css = keep_variants((RUNTIME / "base.css").read_text(encoding="utf-8"), chosen).rstrip()
    core_js = keep_variants((RUNTIME / "core.js").read_text(encoding="utf-8"), chosen).rstrip()
    style_css = (work / "style.css").read_text(encoding="utf-8").rstrip()
    body_html = (work / "body.html").read_text(encoding="utf-8").strip()
    sig_path = work / "signature.js"
    signature = sig_path.read_text(encoding="utf-8").rstrip() if sig_path.exists() else ""

    combo = pick["combo"]
    meta = {k: (v["name"] if isinstance(v, dict) else [o["name"] for o in v]) for k, v in combo.items()}
    meta.update(keyword=keyword, date=stamp, palette_family=pick["palette_family"], allow_counters=pick["allow_counters"])
    config = {"cursor": rt["cursor"], "preloader": rt["preloader"]}
    smooth_attr = "" if rt["smooth"] else ' data-smooth="off"'
    upper = keyword.upper()
    loader = LOADERS[rt["preloader"]].format(label=html.escape(upper))
    sig_block = "\n".join("  " + line if line else "" for line in signature.splitlines())

    page = f"""<!DOCTYPE html>
<html lang="en"{smooth_attr}>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{html.escape(description)}">
<meta name="incubator" content="{html.escape(json.dumps(meta, ensure_ascii=False))}">
<title>{html.escape(title)}</title>
<style>
{base_css}

/* ==========================================================
   {upper} — template styles
   ========================================================== */
{style_css}
</style>
</head>
<body class="is-loading">
<!-- ============ PRELOADER ({rt["preloader"]}) ============ -->
<div class="inc-loader inc-loader--{rt["preloader"]}" id="incLoader" aria-hidden="true">{loader}</div>

{body_html}

<script>
window.INC_CONFIG = {json.dumps(config)};
{core_js}
</script>
<script>
/* ==========================================================
   {upper} — signature effects (uses window.INC runtime)
   ========================================================== */
(() => {{
  'use strict';
  const INC = window.INC;
{sig_block}
}})();
</script>
</body>
</html>
"""
    js = f"window.INC_CONFIG = {json.dumps(config)};\n{core_js}\n(() => {{\nconst INC = window.INC;\n{signature}\n}})();\n"
    return page, js


def validate(page: str, js: str, work: Path, pick: dict, allow_short: bool, env: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    body = (work / "body.html").read_text(encoding="utf-8")
    style = (work / "style.css").read_text(encoding="utf-8")
    lines = page.count("\n") + 1
    own = sum((work / n).read_text(encoding="utf-8").count("\n") for n in ("style.css", "body.html", "signature.js") if (work / n).exists())
    if not allow_short:
        if lines < 500:
            errors.append(f"лише {lines} рядків у шаблоні (< 500)")
        if own < MIN_OWN_LINES:
            errors.append(f"власний код (style+body+signature) лише {own} рядків (< {MIN_OWN_LINES}) — додай змісту/стилів/ефекту")
        target = own_lines_target(env, {"cursor": pick["runtime"]["cursor"], "preloader": pick["runtime"]["preloader"]})
        if own < target:
            warnings.append(f"власний код {own} рядків < цілі {target} → PDF може не набрати INCUBATOR_MIN_PDF_PAGES")
    if 'id="scrollWrap"' not in body:
        errors.append('body.html: немає <div class="scroll-wrap" id="scrollWrap">')
    if "<main" not in body:
        errors.append("body.html: немає <main>")
    if re.search(r'<script[^>]+src=|<link[^>]+href="https?:|@import\s+url\(\s*["\']?https?:', page):
        errors.append("знайдено зовнішні залежності (script src / link / @import)")
    if (err := node_check(js)):
        errors.append(f"JS syntax: {err}")
    if (kf := len(re.findall(r"@keyframes\s", page))) < 8:
        warnings.append(f"лише {kf} @keyframes (ціль 8-10)")
    for bp in ("1200px", "768px", "576px"):
        if f"max-width: {bp}" not in style and f"max-width:{bp}" not in style:
            warnings.append(f"style.css: немає брейкпоінту {bp}")
    if "data-count" in body and not pick["allow_counters"]:
        warnings.append("архітектура без лічильників, але в body є data-count")
    unknown = set(re.findall(r'data-animation="([\w-]+)"', body)) - SUPPORTED_ANIMATIONS
    if unknown:
        warnings.append(f"невідомі data-animation: {sorted(unknown)} (потрібен власний CSS)")
    if not (work / "signature.js").exists():
        warnings.append("немає signature.js — шаблон без власного ефекту")
    return errors, warnings


def make_pdf(src: Path, pdf: Path, title: str, weasy: str) -> None:
    doc = PDF_HEAD.format(title=html.escape(title)) + html.escape(src.read_text(encoding="utf-8"), quote=False) + "</pre></body></html>"
    res = subprocess.run([weasy, "-", str(pdf)], input=doc.encode("utf-8"), capture_output=True)
    if res.returncode != 0 or not pdf.exists():
        raise RuntimeError(f"weasyprint: {res.stderr.decode(errors='ignore')[-400:]}")


def pdf_pages(pdf: Path) -> int:
    """Count pages: read /Count of the /Pages tree (inflating compressed object streams)."""
    data = pdf.read_bytes()
    blobs = [data]
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            blobs.append(zlib.decompress(m.group(1)))
        except zlib.error:
            pass
    blob = b"\n".join(blobs)
    counts = [int(x) for x in re.findall(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", blob)]
    counts += [int(x) for x in re.findall(rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages\b", blob)]
    return max(counts) if counts else len(re.findall(rb"/Type\s*/Page(?![s\w])", blob))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keyword", required=True, help="theme keyword, e.g. 'volt' or 'black cat'")
    ap.add_argument("--concept", required=True, help="concept name for docs and <title>")
    ap.add_argument("--palette", required=True, help="UA: palette/theme description (after «де …»)")
    ap.add_argument("--visual", required=True, help="UA: visual language (after «поєднанні …»)")
    ap.add_argument("--template", help='template name in docs (default: KEYWORD)')
    ap.add_argument("--no-draft", action="store_true", help="skip Gmail draft")
    ap.add_argument("--no-open", action="store_true", help="do not open HTML/PDF")
    ap.add_argument("--allow-short", action="store_true", help="allow < 500 lines")
    ap.add_argument("--check", action="store_true", help="assemble + validate only, write nothing")
    args = ap.parse_args()

    env = load_env()
    min_pdf_pages(env)  # fail early if the page target is not configured
    out, work = output_dir(env), build_dir(env)
    if not (work / "combo.json").exists():
        sys.exit(f"Немає {work}/combo.json — спочатку запусти pick.py")
    for name in ("style.css", "body.html"):
        if not (work / name).exists():
            sys.exit(f"Немає {work}/{name}")
    pick = json.loads((work / "combo.json").read_text(encoding="utf-8"))

    now = dt.datetime.now()
    stamp = now.strftime("%m.%Y")
    keyword = " ".join(args.keyword.split())
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-") or "template"
    page, js = assemble(work, pick, keyword, args.concept, args.concept, stamp)
    errors, warnings = validate(page, js, work, pick, args.allow_short, env)
    lines = page.count("\n") + 1

    for w in warnings:
        print(f"⚠️ {w}")
    if errors:
        for e in errors:
            print(f"❌ {e}")
        sys.exit(1)
    if args.check:
        print(f"✅ CHECK OK: {lines} рядків — нічого не записано")
        return

    out.mkdir(parents=True, exist_ok=True)
    html_path = unique_path(out, slug, stamp)
    pdf_path = html_path.with_suffix(".pdf")
    html_path.write_text(page, encoding="utf-8")
    article = f"{keyword.upper()} {stamp}"
    make_pdf(html_path, pdf_path, f"{article} — Source Code", env.get("INCUBATOR_WEASYPRINT_PATH") or "weasyprint")

    # Page gate BEFORE anything else (archive / open / draft): the PDF must have enough pages
    min_pages = min_pdf_pages(env)  # single source: INCUBATOR_MIN_PDF_PAGES in .env.incubator
    pages = pdf_pages(pdf_path)
    if pages < min_pages:
        per_page = lines / max(pages, 1)
        need = int((min_pages - pages) * per_page) + 25
        html_path.unlink(missing_ok=True)
        pdf_path.unlink(missing_ok=True)
        print(f"❌ PDF має {pages} стор. (< INCUBATOR_MIN_PDF_PAGES={min_pages}). ~{per_page:.0f} рядків/стор. → додай ще ≈{need} рядків "
              f"у style.css / body.html / signature.js і перезапусти build. Лист не створено, файли видалено.")
        sys.exit(2)

    archive = out / ".build" / html_path.stem
    if archive.exists():
        shutil.rmtree(archive)
    shutil.move(str(work), str(archive))

    if not args.no_open:
        subprocess.run(["open", str(html_path)], check=False)
        subprocess.run(["open", str(pdf_path)], check=False)

    doc = DOC.format(
        account=env.get("INCUBATOR_BANK_ACCOUNT", ""), bank=env.get("INCUBATOR_BANK_NAME", ""),
        method=env.get("INCUBATOR_TRANSFER_METHOD", ""), article=article, concept=args.concept,
        palette=args.palette, template=args.template or keyword.upper(), visual=args.visual,
        author=env.get("INCUBATOR_AUTHOR", ""),
    )
    subject = f"Прохання про виведення коштів {stamp}"
    if args.no_draft:
        draft = "пропущено (--no-draft)"
    else:
        try:
            from gmail_draft import create_draft
            draft = create_draft(env.get("INCUBATOR_RECIPIENT_EMAIL", ""), subject, doc, pdf_path,
                                 env.get("INCUBATOR_EMAIL_LABEL", ""), env["_ROOT"])
        except Exception as exc:  # report, never lose the build
            draft = f"❌ помилка: {exc}"

    print(f"✅ BUILD OK: {lines} рядків, {len(re.findall(r'@keyframes', page))} keyframes, PDF {pages} стор.")
    print(f"📄 HTML: {html_path}")
    print(f"📑 PDF:  {pdf_path}")
    print("🌐 Відкрито у браузері та Preview." if not args.no_open else "🌐 Не відкривав (--no-open).")
    print(f"📧 Gmail: {draft} | тема: {subject}")
    print("----- DOC -----")
    print(doc)
    print("----- END DOC -----")


if __name__ == "__main__":
    main()
