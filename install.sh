#!/usr/bin/env bash
# Install GLRP (Grok Long-Running Project) skill into the user Grok skills directory.
#
# Works on: macOS, Linux, Windows (Git Bash or WSL). Requires: bash, git (for one-liner), cp/mkdir.
#
# One-liner (macOS / Linux / Git Bash / WSL):
#   git clone --depth 1 https://github.com/msinclair25/GLRP-Skill.git "${TMPDIR:-/tmp}/GLRP-Skill" && bash "${TMPDIR:-/tmp}/GLRP-Skill/install.sh" && rm -rf "${TMPDIR:-/tmp}/GLRP-Skill"
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# Grok home: respect GROK_HOME; otherwise ~/.grok (HOME works in Git Bash / WSL / macOS / Linux)
GROK_DIR="${GROK_HOME:-${HOME}/.grok}"
DEST="${GROK_DIR}/skills/long-running-project"
SRC="${ROOT}/long-running-project"

if [[ ! -f "${SRC}/SKILL.md" ]]; then
  echo "error: missing ${SRC}/SKILL.md" >&2
  echo "Run install.sh from a full clone of https://github.com/msinclair25/GLRP-Skill" >&2
  exit 1
fi

mkdir -p "$(dirname "${DEST}")"
rm -rf "${DEST}"
# Prefer cp -R (macOS/BSD); fall back to cp -a (GNU) then cp -r
if cp -R "${SRC}" "${DEST}" 2>/dev/null; then
  :
elif cp -a "${SRC}" "${DEST}" 2>/dev/null; then
  :
else
  cp -r "${SRC}" "${DEST}"
fi

# Optional: ensure global AGENTS pointer exists (append if missing)
GLOBAL_AGENTS="${GROK_DIR}/AGENTS.md"
MARKER="long-running-project"
if [[ ! -f "${GLOBAL_AGENTS}" ]] || ! grep -q "${MARKER}" "${GLOBAL_AGENTS}" 2>/dev/null; then
  mkdir -p "$(dirname "${GLOBAL_AGENTS}")"
  cat >> "${GLOBAL_AGENTS}" <<'EOF'

## Long-running projects

When the user says **activate long running project**, **long-running mode**, or similar,
follow the **`long-running-project`** skill (`/long-running-project`).
EOF
  echo "Updated ${GLOBAL_AGENTS} (pointer)"
fi

# Copy playbook next to skill for scaffold discovery
if [[ -f "${ROOT}/docs/PLAYBOOK.md" ]]; then
  mkdir -p "${DEST}/docs"
  cp "${ROOT}/docs/PLAYBOOK.md" "${DEST}/docs/PLAYBOOK.md"
fi

echo "Installed: ${DEST}"
echo
echo "Platform note: macOS/Linux/Git Bash/WSL supported. Native Windows PowerShell:"
echo "  use Git Bash, WSL, or:  bash install.sh  after cloning."
echo
echo "Next:"
echo "  1. Restart Grok or open a new session so skills reload"
echo "  2. In any project:  activate long running project"
echo "     or:             /long-running-project"
echo "  3. Verify:         grok inspect   (look for long-running-project)"
