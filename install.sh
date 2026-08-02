#!/usr/bin/env bash
# Install GLRP (Grok Long-Running Project) skill into the user Grok skills directory.
#
# One-liner (recommended):
#   git clone --depth 1 https://github.com/msinclair25/GLRP-Skill.git /tmp/GLRP-Skill && bash /tmp/GLRP-Skill/install.sh && rm -rf /tmp/GLRP-Skill
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="${GROK_HOME:-$HOME/.grok}/skills/long-running-project"
SRC="$ROOT/long-running-project"

if [[ ! -f "$SRC/SKILL.md" ]]; then
  echo "error: missing $SRC/SKILL.md" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -R "$SRC" "$DEST"

# Optional: ensure global AGENTS pointer exists (append if missing)
GLOBAL_AGENTS="${GROK_HOME:-$HOME/.grok}/AGENTS.md"
MARKER="long-running-project"
if [[ ! -f "$GLOBAL_AGENTS" ]] || ! grep -q "$MARKER" "$GLOBAL_AGENTS" 2>/dev/null; then
  mkdir -p "$(dirname "$GLOBAL_AGENTS")"
  cat >> "$GLOBAL_AGENTS" <<'EOF'

## Long-running projects

When the user says **activate long running project**, **long-running mode**, or similar,
follow the **`long-running-project`** skill (`/long-running-project`).
EOF
  echo "Updated $GLOBAL_AGENTS (pointer)"
fi

# Copy playbook next to skill for scaffold symlink discovery
if [[ -f "$ROOT/docs/PLAYBOOK.md" ]]; then
  mkdir -p "$DEST/docs"
  cp "$ROOT/docs/PLAYBOOK.md" "$DEST/docs/PLAYBOOK.md"
fi

echo "Installed: $DEST"
echo
echo "Next:"
echo "  1. Restart Grok or open a new session so skills reload"
echo "  2. In any project:  activate long running project"
echo "     or:             /long-running-project"
echo "  3. Verify:         grok inspect | grep -i long-running"
