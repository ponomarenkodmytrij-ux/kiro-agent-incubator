#!/usr/bin/env bash
# Incubator agent installer: checks deps, creates config files, registers the agent in ~/.kiro/agents.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="${KIRO_AGENTS_DIR:-$HOME/.kiro/agents}"

echo "▸ Incubator root: $ROOT"
command -v python3 >/dev/null || { echo "❌ python3 not found"; exit 1; }
command -v node >/dev/null || echo "⚠ node not found — JS syntax check will be skipped/fail (brew install node)"
if ! command -v weasyprint >/dev/null && [ ! -x /opt/homebrew/bin/weasyprint ]; then
  echo "⚠ weasyprint not found — install: brew install weasyprint"
fi

[ -f "$ROOT/.env.incubator" ] || { cp "$ROOT/.env.incubator.example" "$ROOT/.env.incubator"; echo "✔ created .env.incubator — fill it in"; }
[ -f "$ROOT/.env.auth" ] || { cp "$ROOT/mcp-server/.env.auth.example" "$ROOT/.env.auth"; echo "✔ created .env.auth — add Gmail address + app password"; }

mkdir -p "$AGENTS_DIR"
ROOT="$ROOT" AGENTS_DIR="$AGENTS_DIR" python3 - <<'PY'
import json, os, shutil
root, out = os.environ["ROOT"], os.environ["AGENTS_DIR"]
cfg = json.load(open(f"{root}/agent/incubator.json", encoding="utf-8"))
cfg["prompt"] = open(f"{root}/agent/prompt.md", encoding="utf-8").read().replace("{{ROOT}}", root)
# Optional fallback MCP (the build script already creates drafts itself via stdlib IMAP)
uv = shutil.which("uv")
if uv:
    cfg["mcpServers"] = {"gmail": {"command": uv, "args": [
        "run", "--with", "mcp[cli]", "--with", "python-dotenv",
        "python", f"{root}/mcp-server/gmail_draft_server.py"]}}
else:
    cfg["tools"] = [t for t in cfg["tools"] if not t.startswith("@gmail")]
    cfg["allowedTools"] = [t for t in cfg["allowedTools"] if not t.startswith("@gmail")]
    print("⚠ uv not found — Gmail MCP fallback not registered (draft creation via build.py still works)")
path = f"{out}/incubator.json"
json.dump(cfg, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"✔ agent written: {path}")
PY
echo
echo "Next: edit $ROOT/.env.incubator and $ROOT/.env.auth, then run: kiro-cli chat --agent incubator"
