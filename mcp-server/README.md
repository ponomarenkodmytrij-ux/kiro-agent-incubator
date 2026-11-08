# Gmail Drafts MCP Server

Minimal MCP server that exposes **one tool**: `gmail_create_draft_with_attachment`.

Designed for the Incubator agent — creates email drafts with PDF attachments.

## Security

- Only creates drafts (never sends, reads, or searches emails)
- Validates email address format
- Validates attachment files: must exist, ≤25 MB, no executable extensions
- Credentials stored in `.env.auth` (never hardcoded)
- No OAuth complexity — uses Google App Password via IMAP

## Setup

### 1. Get a Google App Password

1. Enable 2-Step Verification on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a password for "Mail"

### 2. Configure credentials

```bash
cp .env.auth.example .env.auth
# Edit .env.auth with your email and app password
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
# or
uv pip install -r requirements.txt
```

### 4. Add to Kiro MCP config

Add to your `.kiro/settings/mcp.json` (workspace or user level):

```json
{
  "mcpServers": {
    "gmail-drafts": {
      "command": "python",
      "args": ["path/to/kiro-agent-incubator/mcp-server/gmail_draft_server.py"],
      "disabled": false,
      "autoApprove": ["gmail_create_draft_with_attachment"]
    }
  }
}
```

Or with `uv`:

```json
{
  "mcpServers": {
    "gmail-drafts": {
      "command": "uv",
      "args": ["run", "path/to/kiro-agent-incubator/mcp-server/gmail_draft_server.py"],
      "disabled": false,
      "autoApprove": ["gmail_create_draft_with_attachment"]
    }
  }
}
```

## Blocked file extensions

The following extensions are blocked from being attached:
`.exe`, `.bat`, `.cmd`, `.com`, `.msi`, `.scr`, `.pif`, `.vbs`, `.js`, `.ws`, `.wsf`, `.wsc`, `.wsh`, `.ps1`, `.psm1`, `.psd1`, `.sh`, `.bash`, `.zsh`
