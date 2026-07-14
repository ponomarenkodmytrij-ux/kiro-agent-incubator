# Incubator Power

Generate Awwwards-level single-page web templates with premium animations, custom inertial scroll, magnetic cursor, and artistic visual direction — all from 1-4 keywords.

## Installation

1. Copy the entire `incubator/` folder to `~/.kiro/powers/installed/incubator/`
2. Copy `.env.incubator.example` to your workspace root as `.env.incubator`
3. Fill in your personal details in `.env.incubator`
4. Restart Kiro or reload powers

## Structure

```
incubator/
├── POWER.md                    # Power manifest
├── .env.incubator.example      # Config template (copy to workspace root)
├── README.md                   # This file
├── steering/
│   ├── workflow.md             # Generation protocol
│   └── ui-library.md          # UI effects pool for variety
└── mcp-server/
    ├── gmail_draft_server.py   # Minimal Gmail MCP (1 tool only)
    ├── .env.auth.example       # Gmail credentials template
    ├── requirements.txt        # Python dependencies
    └── README.md               # MCP server setup guide
```

## Configuration

The `.env.incubator` file in your workspace root controls:

| Variable | Description | Example |
|----------|-------------|---------|
| `INCUBATOR_AUTHOR` | Your name for signatures | `John Doe` |
| `INCUBATOR_BANK_ACCOUNT` | Bank account for payment text | `00 0000 0000 ...` |
| `INCUBATOR_BANK_NAME` | Bank name | `Pekao` |
| `INCUBATOR_TRANSFER_METHOD` | Transfer type | `експрес переказом` |
| `INCUBATOR_RECIPIENT_EMAIL` | Email for drafts | `someone@example.com` |
| `INCUBATOR_EMAIL_LABEL` | Gmail label (optional) | `Invoices` |
| `INCUBATOR_WEASYPRINT_PATH` | Path to weasyprint | `/opt/homebrew/bin/weasyprint` |
| `INCUBATOR_OUTPUT_DIR` | Where to save files | `{workspace}/output` |

## Prerequisites

- **weasyprint** — for PDF generation. Install via `brew install weasyprint` (macOS) or `pip install weasyprint`
- **macOS** — uses `open` command to launch browser/preview (adapt for your OS)
- **Gmail MCP** (optional) — for email draft creation. See `mcp-server/README.md` for setup

## Usage

1. Activate the power in Kiro chat
2. Enter 1-4 keywords (e.g., `obsidian`, `aurora silk`, `neon brutalism`)
3. The agent generates a complete single-page HTML template + PDF
4. Optionally creates a Gmail draft with documentation

## Output

Each generation produces:
- `output/[keyword]-[MM.YYYY].html` — Production-ready single-file template
- `output/[keyword]-[MM.YYYY].pdf` — Source code in printable format
