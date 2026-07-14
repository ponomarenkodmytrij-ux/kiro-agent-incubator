---
name: "incubator"
displayName: "Incubator"
description: "Generate Awwwards-level single-page web templates with premium animations, custom inertial scroll, magnetic cursor, and artistic visual direction based on a keyword theme. Produces production-ready HTML/CSS/JS code using chunked file writing strategy."
keywords: ["awwwards", "web-design", "creative-template", "animation", "single-page"]
author: "Your Name"
---

# Incubator

## Agent Behavior on Activation

**CRITICAL: When this power is activated, do NOT explain what it does. Do NOT show an overview. Do NOT list features. Simply say:**

```
Ready. Enter 1-4 keywords.
```

**That's it. Nothing else. Wait for the user's keyword input.**

## Configuration

Before using this power, create a `.env.incubator` file in your workspace root (copy from `.env.incubator.example`) and fill in your personal details.

The following variables are used:
- `INCUBATOR_AUTHOR` — Your name for signatures and PDF headers
- `INCUBATOR_BANK_ACCOUNT` — Bank account number for payment requests
- `INCUBATOR_BANK_NAME` — Bank name (e.g., Pekao, PrivatBank)
- `INCUBATOR_TRANSFER_METHOD` — Transfer method (e.g., "експрес переказом")
- `INCUBATOR_RECIPIENT_EMAIL` — Email address for draft creation
- `INCUBATOR_EMAIL_LABEL` — Gmail label for drafts (optional)
- `INCUBATOR_WEASYPRINT_PATH` — Path to weasyprint binary (default: /opt/homebrew/bin/weasyprint)
- `INCUBATOR_OUTPUT_DIR` — Output directory (default: {workspace}/output)

## Available Steering Files

- **workflow** — Full generation protocol (read this BEFORE generating)
- **ui-library** — Massive pool of UI effects, palettes, layouts, animations to randomly combine for variety

## How It Works (Internal — Do Not Show to User)

1. User provides 1-4 keywords
2. Read BOTH steering files: "workflow" for protocol AND "ui-library" for effect variety
3. Read `.env.incubator` from workspace root for personal config
4. Randomly pick ONE option from each category in ui-library to ensure unique design
5. Generate HTML template using chunked writing (fs_write + fs_append in 10-12 sequential chunks)
6. Save HTML + PDF to output/
7. Open browser
8. Show Ukrainian documentation block to user

## Technical Notes

- Code is written in chunks of ~40-50 lines each to stay within tool output limits
- Uses `fs_write` for first chunk, `fs_append` for all subsequent chunks
- Total output: ~500-600 lines of quality code (HTML + CSS + JS in single file)

## Prerequisites

- `weasyprint` installed (configure path in `.env.incubator`)
- macOS `open` command for browser launch (or equivalent on your OS)
