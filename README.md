# Incubator Agent

Kiro agent that generates Awwwards-level single-page HTML templates from a visual theme (or just `go`). Deterministic work is done by scripts; the agent writes only the creative part (CSS / HTML / JS).

Pipeline: `pick.py` chooses a design combination (avoiding recent ones) → agent writes `style.css`, `body.html`, `signature.js` → `build.py` assembles HTML, renders a PDF, checks the minimum page count, opens both files and creates a Gmail **draft** (never sends).

## Quick start

```bash
git clone https://github.com/ponomarenkodmytrij-ux/kiro-agent-incubator.git
cd kiro-agent-incubator
./install.sh
```

`install.sh`:
- checks `python3`, `node`, `weasyprint`;
- creates `.env.incubator` and `.env.auth` from the examples (if missing);
- registers the agent in `~/.kiro/agents/incubator.json` with absolute paths for **this** checkout (re-run it if you move the folder).

Then:
1. Fill in `.env.incubator` (see below) and `.env.auth` (Gmail address + [app password](https://myaccount.google.com/apppasswords)).
2. Start the agent: `kiro-cli chat --agent incubator`
3. Type `go` (or 1-4 keywords).

## Requirements

| Tool | Why |
|------|-----|
| Python 3.9+ | scripts (stdlib only) |
| Node.js | `node --check` for the generated JS |
| weasyprint | HTML → PDF (`brew install weasyprint`) |
| macOS | `open` is used to show results (adapt `build.py` for other OS) |
| uv (optional) | only for the fallback Gmail MCP server |

## Configuration

`.env.incubator` (repo root, git-ignored — never commit it):

| Variable | Description |
|----------|-------------|
| `INCUBATOR_AUTHOR` | Name for signatures / PDF header |
| `INCUBATOR_BANK_ACCOUNT` | Account number used in the payment-request text |
| `INCUBATOR_BANK_NAME` | Bank name |
| `INCUBATOR_TRANSFER_METHOD` | Transfer type |
| `INCUBATOR_RECIPIENT_EMAIL` | Recipient of the Gmail draft |
| `INCUBATOR_EMAIL_LABEL` | Gmail label for drafts (optional) |
| `INCUBATOR_WEASYPRINT_PATH` | Path to the `weasyprint` binary |
| `INCUBATOR_OUTPUT_DIR` | Output folder (`{workspace}` = folder with `.env.incubator`) |
| `INCUBATOR_MIN_PDF_PAGES` | Minimum PDF pages; the build fails (exit 2) below this |

`.env.auth` (git-ignored): `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`.

Both files are found by searching upwards from `scripts/`, so they can also live in a parent workspace folder. Overrides: `INCUBATOR_ENV`, `INCUBATOR_AUTH_FILE`.

## Structure

```
.
├── install.sh              # setup + agent registration
├── agent/
│   ├── incubator.json      # agent config template
│   └── prompt.md           # agent prompt template ({{ROOT}} is substituted)
├── scripts/
│   ├── pick.py             # chooses design combo, creates the build dir
│   ├── build.py            # assemble → validate → PDF → open → Gmail draft
│   ├── common.py           # shared helpers
│   └── gmail_draft.py      # IMAP draft creation (stdlib)
├── runtime/                # base.css + core.js inlined into every template
├── steering/
│   ├── workflow.md         # generation protocol (read by the agent)
│   └── ui-library.md       # pool of design options (read by pick.py)
├── mcp-server/             # optional fallback Gmail MCP server
└── .env.incubator.example
```

## Output

Each run writes to `output/`:
- `<keyword>-<MM.YYYY>.html` — single-file template
- `<keyword>-<MM.YYYY>.pdf` — printable source code

The agent replies with the documentation block and the HTML / PDF / Gmail status lines.

## Troubleshooting

- `⚠ Файл .env.incubator не знайдено` — run `./install.sh` or copy the example manually.
- Exit 2 from `build.py` — PDF has fewer pages than `INCUBATOR_MIN_PDF_PAGES`; the agent adds more content and reruns.
- Gmail error — check `.env.auth`; `build.py --no-draft` skips the draft step.
