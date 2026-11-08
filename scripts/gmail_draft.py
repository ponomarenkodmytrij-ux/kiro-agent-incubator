"""Create a Gmail draft with an attachment via IMAP (stdlib only).

Port of mcp-server/gmail_draft_server.py so build.py can create the draft
without an MCP round-trip. Credentials: GMAIL_ADDRESS / GMAIL_APP_PASSWORD
from .env.auth (INCUBATOR_AUTH_FILE override, else searched upwards).

CLI: python3 gmail_draft.py --check   → login test only, creates nothing.
"""
from __future__ import annotations

import base64
import imaplib
import mimetypes
import os
import re
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from common import SCRIPTS, parse_kv

IMAP_HOST = "imap.gmail.com"
MAX_MB = 25


def load_credentials(root: str | None = None) -> tuple[str, str]:
    override = os.environ.get("INCUBATOR_AUTH_FILE")
    bases = ([Path(root)] if root else []) + list(SCRIPTS.parents)
    candidates = [Path(override)] if override else [b / ".env.auth" for b in bases]
    path = next((c for c in candidates if c.is_file()), None)
    creds = parse_kv(path) if path else {}
    addr = os.environ.get("GMAIL_ADDRESS") or creds.get("GMAIL_ADDRESS", "")
    pwd = os.environ.get("GMAIL_APP_PASSWORD") or creds.get("GMAIL_APP_PASSWORD", "")
    if not addr or not pwd:
        raise RuntimeError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD не знайдено (.env.auth)")
    return addr, pwd


def _decode_utf7(s: str) -> str:
    """Decode IMAP modified UTF-7 folder names."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "&":
            end = s.index("-", i + 1)
            chunk = s[i + 1:end]
            if not chunk:
                out.append("&")
            else:
                chunk = chunk.replace(",", "/")
                chunk += "=" * (-len(chunk) % 4)
                out.append(base64.b64decode(chunk).decode("utf-16-be"))
            i = end + 1
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _folders(conn: imaplib.IMAP4_SSL) -> list[tuple[str, str]]:
    """Return (flags_line, raw_name) for every folder."""
    status, data = conn.list()
    result = []
    if status == "OK":
        for item in data:
            line = item.decode()
            parts = line.split('"')
            if len(parts) >= 5:
                result.append((line, parts[-2]))
    return result


def _drafts_folder(conn: imaplib.IMAP4_SSL) -> str:
    for line, name in _folders(conn):
        if "\\Drafts" in line:
            return name
    return "[Gmail]/Drafts"


def _label_folder(conn: imaplib.IMAP4_SSL, label: str) -> str | None:
    for _, name in _folders(conn):
        try:
            readable = _decode_utf7(name)
        except Exception:
            readable = name
        if readable.lower() == label.lower():
            return name
    return None


def create_draft(to: str, subject: str, body: str, attachment: Path, label: str = "", root: str | None = None) -> str:
    if not re.match(r"^[\w.%+\-]+@[\w.\-]+\.[A-Za-z]{2,}$", to.strip()):
        raise ValueError(f"Невалідна адреса: {to}")
    attachment = Path(attachment)
    if not attachment.is_file() or attachment.stat().st_size > MAX_MB * 1024 * 1024:
        raise ValueError(f"Вкладення відсутнє або > {MAX_MB}MB: {attachment}")
    addr, pwd = load_credentials(root)

    msg = MIMEMultipart()
    msg["From"], msg["To"], msg["Subject"] = addr, to.strip(), subject.strip()
    msg.attach(MIMEText(body, "plain", "utf-8"))
    main_type, sub_type = (mimetypes.guess_type(str(attachment))[0] or "application/octet-stream").split("/", 1)
    part = MIMEBase(main_type, sub_type)
    part.set_payload(attachment.read_bytes())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=attachment.name)
    msg.attach(part)

    conn = imaplib.IMAP4_SSL(IMAP_HOST)
    try:
        conn.login(addr, pwd)
        drafts = _drafts_folder(conn)
        status, _ = conn.append(drafts, "\\Draft", None, msg.as_bytes())
        if status != "OK":
            raise RuntimeError(f"IMAP append failed: {status}")
        note = ""
        if label:
            folder = _label_folder(conn, label)
            if folder:
                conn.select(drafts)
                status, data = conn.search(None, "ALL")
                if status == "OK" and data[0]:
                    conn.copy(data[0].split()[-1], folder)
                    note = f" | лейбл «{label}»"
            else:
                note = f" | ⚠️ лейбл «{label}» не знайдено"
        return f"чернетку створено ({attachment.name}){note}"
    finally:
        try:
            conn.logout()
        except Exception:
            pass


if __name__ == "__main__":
    if "--check" in sys.argv:
        a, p = load_credentials()
        c = imaplib.IMAP4_SSL(IMAP_HOST)
        c.login(a, p)
        print("IMAP login OK, drafts folder:", _drafts_folder(c))
        c.logout()
