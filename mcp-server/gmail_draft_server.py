"""Minimal MCP server for creating Gmail drafts with attachments.

Uses Google App Password via IMAP — no OAuth flow needed.
Only exposes ONE tool: create_draft_with_attachment.

Security:
- Validates attachment paths (must exist, max 25MB, restricted extensions)
- Validates email addresses format
- Does NOT expose email reading, search, or sending capabilities
- Credentials loaded from .env.auth in workspace root
"""

import imaplib
import base64
import mimetypes
import os
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ── Configuration ─────────────────────────────────────────────────

# Load credentials from workspace .env.auth
_env_path = Path(__file__).resolve().parent.parent / ".env.auth"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Try parent directories (workspace root)
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env.auth"
        if candidate.exists():
            load_dotenv(candidate)
            break

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
IMAP_HOST = "imap.gmail.com"

# Security limits
MAX_ATTACHMENT_SIZE_MB = 25
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".com", ".msi", ".scr", ".pif",
    ".vbs", ".js", ".ws", ".wsf", ".wsc", ".wsh",
    ".ps1", ".psm1", ".psd1",
    ".sh", ".bash", ".zsh",
}

# ── MCP Server ────────────────────────────────────────────────────

mcp = FastMCP(
    "gmail-drafts",
    description="Create Gmail drafts with attachments via IMAP. Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env.auth.",
)


# ── Helpers ───────────────────────────────────────────────────────

def _validate_email(addr: str) -> bool:
    """Basic email format validation."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, addr.strip()))


def _validate_attachment(path: str) -> tuple[bool, str]:
    """Validate attachment file exists, is within size limits, and has safe extension."""
    file_path = Path(path)

    if not file_path.exists():
        return False, f"File not found: {path}"

    if not file_path.is_file():
        return False, f"Not a regular file: {path}"

    # Check size
    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_ATTACHMENT_SIZE_MB:
        return False, f"File too large: {size_mb:.1f}MB (max {MAX_ATTACHMENT_SIZE_MB}MB)"

    # Check extension
    ext = file_path.suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        return False, f"Blocked file extension: {ext}"

    return True, ""


def _imap_connect() -> imaplib.IMAP4_SSL:
    """Connect to Gmail IMAP with credentials."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "Gmail credentials not configured. "
            "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env.auth"
        )
    conn = imaplib.IMAP4_SSL(IMAP_HOST)
    conn.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    return conn


def _find_drafts_folder(conn: imaplib.IMAP4_SSL) -> str:
    """Find the Drafts folder name (varies by locale)."""
    status, folders = conn.list()
    if status == "OK":
        for folder_info in folders:
            decoded = folder_info.decode()
            if "\\Drafts" in decoded:
                parts = decoded.split('"')
                if len(parts) >= 5:
                    return parts[-2]
    # Fallback
    for name in ["[Gmail]/Drafts", "[Gmail]/&BCcENQRABD0ENQRCBDoEOA-"]:
        try:
            status, _ = conn.select(name)
            if status == "OK":
                return name
        except Exception:
            continue
    return "[Gmail]/Drafts"


def _decode_imap_utf7(s: str) -> str:
    """Decode IMAP modified UTF-7 encoded string."""
    result = []
    i = 0
    while i < len(s):
        if s[i] == '&':
            end = s.index('-', i + 1) if '-' in s[i + 1:] else len(s)
            if end == i + 1:
                result.append('&')
            else:
                encoded = s[i + 1:end]
                encoded = encoded.replace(',', '/')
                padding = 4 - len(encoded) % 4
                if padding != 4:
                    encoded += '=' * padding
                decoded_bytes = base64.b64decode(encoded)
                result.append(decoded_bytes.decode('utf-16-be'))
            i = end + 1
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


def _apply_label(conn: imaplib.IMAP4_SSL, drafts_folder: str, label: str) -> str:
    """Apply a Gmail label to the latest draft by copying it to the label folder."""
    label_folder = None
    status, folders = conn.list()
    if status == "OK":
        for folder_info in folders:
            decoded_line = folder_info.decode()
            parts = decoded_line.split('"')
            if len(parts) >= 5:
                folder_name = parts[-2]
                try:
                    readable = _decode_imap_utf7(folder_name)
                    if readable.lower() == label.lower():
                        label_folder = folder_name
                        break
                except Exception:
                    if folder_name.lower() == label.lower():
                        label_folder = folder_name
                        break

    if not label_folder:
        return f"Label '{label}' not found"

    conn.select(drafts_folder)
    status, data = conn.search(None, "ALL")
    if status == "OK" and data[0]:
        msg_ids = data[0].split()
        latest = msg_ids[-1]
        status, _ = conn.copy(latest, label_folder)
        if status == "OK":
            return f"Label '{label}' applied"
        return f"Failed to apply label: {status}"
    return "No draft found to label"


# ── Tool ──────────────────────────────────────────────────────────


@mcp.tool()
def gmail_create_draft_with_attachment(
    to: str,
    subject: str,
    body: str,
    attachment_path: str,
    cc: str = "",
    bcc: str = "",
    label: str = "",
) -> str:
    """Create a draft email with a file attachment (saves to Gmail Drafts folder).

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        attachment_path: Absolute path to the file to attach
        cc: CC recipients (comma-separated, optional)
        bcc: BCC recipients (comma-separated, optional)
        label: Gmail label to apply to the draft (optional, e.g. 'Інкубатор')
    """
    # ── Validate inputs ───────────────────────────────────────────
    if not to or not to.strip():
        return "Error: 'to' address is required"

    # Validate all email addresses
    all_recipients = [to] + ([r.strip() for r in cc.split(",") if r.strip()] if cc else [])
    for addr in all_recipients:
        if not _validate_email(addr):
            return f"Error: Invalid email address: {addr}"

    if not subject or not subject.strip():
        return "Error: 'subject' is required"

    if not body or not body.strip():
        return "Error: 'body' is required"

    if not attachment_path or not attachment_path.strip():
        return "Error: 'attachment_path' is required"

    # Validate attachment
    valid, error_msg = _validate_attachment(attachment_path)
    if not valid:
        return f"Error: {error_msg}"

    file_path = Path(attachment_path)

    # ── Build message ─────────────────────────────────────────────
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to.strip()
    msg["Subject"] = subject.strip()
    if cc:
        msg["Cc"] = cc.strip()

    # Body
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attachment
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"
    main_type, sub_type = mime_type.split("/", 1)

    with open(file_path, "rb") as f:
        attachment = MIMEBase(main_type, sub_type)
        attachment.set_payload(f.read())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=file_path.name,
    )
    msg.attach(attachment)

    # ── Save to Drafts via IMAP ───────────────────────────────────
    conn = _imap_connect()
    try:
        drafts_folder = _find_drafts_folder(conn)
        conn.select(drafts_folder)
        status, _ = conn.append(drafts_folder, "\\Draft", None, msg.as_bytes())
        if status == "OK":
            label_msg = ""
            if label and label.strip():
                label_msg = " | " + _apply_label(conn, drafts_folder, label.strip())
            return (
                f"✅ Draft created with attachment.\n"
                f"To: {to}\n"
                f"Subject: {subject}\n"
                f"Attachment: {file_path.name} ({file_path.stat().st_size / 1024:.0f} KB)"
                f"{label_msg}"
            )
        return f"Error: Failed to create draft (IMAP status: {status})"
    finally:
        conn.logout()


# ── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
