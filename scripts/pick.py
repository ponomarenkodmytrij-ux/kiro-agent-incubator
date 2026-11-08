#!/usr/bin/env python3
"""Incubator design picker.

Randomly picks one option per axis from steering/ui-library.md, avoiding what
the last N generated templates used (read from <meta name="incubator">).
Writes <output>/.build/current/combo.json and prints a compact brief.

Usage: pick.py [--history 4] [--seed N]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys

from common import LIBRARY, build_dir, load_env, min_pdf_pages, output_dir, own_lines_target, read_history

AXES = {
    "COLOR PALETTES": "palette", "TYPOGRAPHY SYSTEMS": "typography", "LAYOUT PATTERNS": "layout",
    "HERO SECTION STYLES": "hero", "SCROLL ANIMATION STYLES": "reveals", "CURSOR EFFECTS": "cursor",
    "HOVER EFFECTS FOR CARDS": "hover", "BACKGROUND EFFECTS": "background", "PRELOADER STYLES": "preloader",
    "MICRO-INTERACTIONS": "micro", "NAVIGATION STYLES": "nav", "SPECIAL UNIQUE FEATURES": "special",
    "SECTION DIVIDER STYLES": "divider", "SECTION ARCHITECTURE": "architecture",
    "SHAPE & FORM LANGUAGE": "shape", "SPATIAL DENSITY": "density", "TONAL MOOD": "mood",
}
# Library option → runtime implementation id
CURSOR_MAP = {"Dot + Ring": "ring", "Cross Hairs": "crosshair", "Invert Blend": "blend",
              "Text Label": "label", "Trail Particles": "trail", "Spotlight": "spotlight"}
PRELOADER_MAP = {"Counter Percentage": "counter", "Progress Bar Minimal": "bar", "Grid Fill": "grid",
                 "Curtain Split": "curtain", "Fade Words": "words", "Vertical Blinds": "blinds"}
REVEAL_MAP = {"Fade Up": "fade-up", "Blur In": "blur", "Scale Pop": "scale", "Slide From Left": "slide-l",
              "Slide From Right": "slide-r", "Clip Reveal Horizontal": "clip-h", "Clip Reveal Vertical": "clip-v",
              "Rotate In": "rotate", "Skew Slide": "skew", "Split Lines": "split", "Flip In": "flip",
              "Elastic Bounce": "elastic", "Morph Shape": "morph", "Color Shift": "grayscale",
              "Outline Draw": "draw", "Pixel Dissolve": "pixel", "Accordion Unfold": "unfold"}
# Layouts/recipes that need native scrolling (position: sticky / scroll-snap / pinned panels)
NATIVE_SCROLL = {"Horizontal Scroll Story", "Full-Screen Snap Panels", "Split Screen Dual", "Overlapping Cards Stack",
                 "Sticky Layers", "Index/Table-of-Contents", "Off-Canvas Horizontal Drawer", "Asymmetric Two-Thirds",
                 "Horizontal Chapters", "Stacking Cards on Scroll", "Horizontal Scroll Section"}
COUNTER_RECIPES = {"Classic Product-ish", "Bento Dashboard"}
MOODS_BY_FAMILY = {
    "Dark": ["Pitch Dark", "High-Contrast Punch", "Cool / Clinical"],
    "Light": ["Bright / Optimistic", "Cool / Clinical", "Muted / Editorial"],
    "Duotone": ["Pitch Dark", "High-Contrast Punch", "Warm / Analog"],
    "Bold": ["High-Contrast Punch", "Bright / Optimistic", "Pitch Dark"],
    "Muted": ["Muted / Editorial", "Warm / Analog", "Cool / Clinical"],
    "Vivid": ["Bright / Optimistic", "High-Contrast Punch"],
}
HEAD_RE = re.compile(r"^##\s+\W*\s*([A-Z][A-Z0-9 &/\-]+?)\s*\(pick")
ITEM_RE = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*\s*[—-]\s*(.+)$")


def parse_library() -> dict[str, list[dict]]:
    lib: dict[str, list[dict]] = {}
    axis, family = None, ""
    for line in LIBRARY.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            m = HEAD_RE.match(line)
            axis = AXES.get(m.group(1).strip()) if m else None
            family = ""
            continue
        if line.startswith("### "):
            family = line[4:].split()[0].split("/")[0]  # "Dark", "Light", "Duotone", "Bold", "Muted", "Vivid"
            continue
        m = ITEM_RE.match(line.strip())
        if axis and m:
            lib.setdefault(axis, []).append({"name": m.group(1).strip(), "desc": m.group(2).strip(), "family": family})
    missing = sorted(set(AXES.values()) - set(lib))
    if missing:
        sys.exit(f"ui-library.md: не знайдено осей {missing}")
    return lib


def choose(options: list[dict], avoid: set[str], keep=lambda o: True) -> dict:
    pool = [o for o in options if keep(o) and o["name"] not in avoid] or [o for o in options if keep(o)] or options
    return random.choice(pool)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--history", type=int, default=4, help="how many recent templates to avoid")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    random.seed(args.seed)

    env = load_env()
    lib = parse_library()
    hist = read_history(output_dir(env), args.history)
    used = lambda key, n=args.history: {h.get(key) for h in hist[:n] if h.get(key)}

    combo: dict = {}
    # Skeleton first — the strongest anti-sameness axes avoid the whole history window
    no_counters_now = bool(hist and hist[0].get("allow_counters"))
    combo["architecture"] = choose(lib["architecture"], used("architecture"),
                                   lambda o: not (no_counters_now and o["name"] in COUNTER_RECIPES))
    for key in ("layout", "hero", "shape", "nav", "special", "typography"):
        combo[key] = choose(lib[key], used(key))
    allow_counters = combo["architecture"]["name"] in COUNTER_RECIPES
    if combo["special"]["name"] == "Scroll-Triggered Counter" and not allow_counters:
        combo["special"] = choose(lib["special"], used("special") | {"Scroll-Triggered Counter"})

    # Palette: new palette, and a different family than the previous template
    last_family = hist[0].get("palette_family") if hist else None
    combo["palette"] = choose(lib["palette"], used("palette"), lambda o: o["family"] != last_family)
    family = combo["palette"]["family"]
    moods = MOODS_BY_FAMILY.get(family, [])
    combo["mood"] = choose(lib["mood"], used("mood", 1), lambda o: any(o["name"].startswith(m) for m in moods))
    combo["density"] = choose(lib["density"], used("density", 2))
    for key in ("hover", "background", "divider"):
        combo[key] = choose(lib[key], used(key, 1))
    combo["cursor"] = choose(lib["cursor"], used("cursor"), lambda o: o["name"] in CURSOR_MAP)
    combo["preloader"] = choose(lib["preloader"], used("preloader"), lambda o: o["name"] in PRELOADER_MAP)
    reveals = [o for o in lib["reveals"] if o["name"] in REVEAL_MAP]
    combo["reveals"] = random.sample(reveals, 4)
    combo["micro"] = random.sample(lib["micro"], 3)

    native = any(combo[k]["name"] in NATIVE_SCROLL for k in ("layout", "architecture", "special"))
    result = {
        "combo": combo,
        "palette_family": family,
        "allow_counters": allow_counters,
        "runtime": {
            "cursor": CURSOR_MAP[combo["cursor"]["name"]],
            "preloader": PRELOADER_MAP[combo["preloader"]["name"]],
            "smooth": not native,
            "reveals": [REVEAL_MAP[o["name"]] for o in combo["reveals"]],
        },
        "avoided": len(hist),
    }

    work = build_dir(env)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "combo.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    # Compact brief for the agent (this is all it needs to read)
    print(f"BUILD DIR: {work}")
    print(f"history avoided: {len(hist)} | counters: {'yes' if allow_counters else 'NO'} | "
          f"smooth scroll: {'on' if not native else 'off (native — sticky/snap allowed)'}")
    for key in ("architecture", "layout", "shape", "density", "mood", "palette", "typography", "hero",
                "nav", "special", "hover", "background", "divider"):
        o = combo[key]
        print(f"{key}: {o['name']} — {o['desc']}")
    rt = result["runtime"]
    print(f"cursor (runtime): {rt['cursor']} | preloader (runtime): {rt['preloader']}")
    print(f"reveals (data-animation): {', '.join(r if r != 'split' else 'split → use data-split' for r in rt['reveals'])}")
    print("micro: " + "; ".join(o["name"] for o in combo["micro"]))
    pages = min_pdf_pages(env)
    target = own_lines_target(env, {"cursor": rt["cursor"], "preloader": rt["preloader"]})
    print(f"PDF target: ≥ {pages} pages (INCUBATOR_MIN_PDF_PAGES) → write ≈ {target}+ lines in style.css + body.html + signature.js")


if __name__ == "__main__":
    main()
