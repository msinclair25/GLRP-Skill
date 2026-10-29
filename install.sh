#!/usr/bin/env bash
# Install GLRP (Grok Long-Running Project) skill into the user Grok skills directory.
#
# Works on: macOS, Linux, Windows (Git Bash or WSL). Requires: bash, git (for one-liner), cp/mkdir.
#
# One-liner (macOS / Linux / Git Bash / WSL):
#   glrp_tmp="$(mktemp -d)" && (trap 'rm -rf "$glrp_tmp"' EXIT; git clone --depth 1 https://github.com/msinclair25/GLRP-Skill.git "$glrp_tmp/GLRP-Skill" && bash "$glrp_tmp/GLRP-Skill/install.sh")
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# Grok home: respect GROK_HOME; otherwise ~/.grok (HOME works in Git Bash / WSL / macOS / Linux)
if [[ -n "${GROK_HOME:-}" ]]; then
  GROK_DIR="${GROK_HOME}"
elif [[ -n "${HOME:-}" ]]; then
  GROK_DIR="${HOME}/.grok"
else
  echo "error: neither GROK_HOME nor HOME is set" >&2
  exit 1
fi
DEST="${GROK_DIR}/skills/long-running-project"
SRC="${ROOT}/long-running-project"

if [[ ! -f "${SRC}/SKILL.md" ]]; then
  echo "error: missing ${SRC}/SKILL.md" >&2
  echo "Run install.sh from a full clone of https://github.com/msinclair25/GLRP-Skill" >&2
  exit 1
fi

SKILLS_DIR="$(dirname "${DEST}")"
mkdir -p "${SKILLS_DIR}"

# Build the replacement completely before moving the current install aside.
# A failed copy therefore leaves the working skill untouched.
STAGING_ROOT="$(mktemp -d "${SKILLS_DIR}/.glrp-install.XXXXXX")"
STAGED_DEST="${STAGING_ROOT}/long-running-project"
PREVIOUS_DEST="${STAGING_ROOT}/previous"
had_previous=0

cleanup() {
  status=$?
  keep_staging=0
  trap - EXIT
  if [[ ${status} -ne 0 && ${had_previous} -eq 1 && ! -e "${DEST}" && ! -L "${DEST}" && -e "${PREVIOUS_DEST}" ]]; then
    if ! mv "${PREVIOUS_DEST}" "${DEST}"; then
      keep_staging=1
      echo "error: could not restore the previous skill; backup retained at ${PREVIOUS_DEST}" >&2
    fi
  fi
  if [[ ${keep_staging} -eq 0 ]]; then
    rm -rf "${STAGING_ROOT}"
  fi
  exit "${status}"
}
trap cleanup EXIT

cp -R "${SRC}" "${STAGED_DEST}"

# Copy the full playbook into the staged skill before it becomes active.
if [[ -f "${ROOT}/docs/PLAYBOOK.md" ]]; then
  mkdir -p "${STAGED_DEST}/docs"
  cp "${ROOT}/docs/PLAYBOOK.md" "${STAGED_DEST}/docs/PLAYBOOK.md"
fi

if [[ -e "${DEST}" || -L "${DEST}" ]]; then
  had_previous=1
  mv "${DEST}" "${PREVIOUS_DEST}"
fi
mv "${STAGED_DEST}" "${DEST}"

# Optional: ensure global AGENTS pointer exists (append if missing)
GLOBAL_AGENTS="${GROK_DIR}/AGENTS.md"
MARKER="<!-- GLRP-SKILL-POINTER -->"
LEGACY_MARKER='follow the **`long-running-project`** skill'
if [[ -L "${GLOBAL_AGENTS}" ]]; then
  echo "Skipped ${GLOBAL_AGENTS} pointer (file is a symlink; target left unchanged)"
elif [[ ! -f "${GLOBAL_AGENTS}" ]] || { ! grep -Fq "${MARKER}" "${GLOBAL_AGENTS}" 2>/dev/null && ! grep -Fq "${LEGACY_MARKER}" "${GLOBAL_AGENTS}" 2>/dev/null; }; then
  if mkdir -p "$(dirname "${GLOBAL_AGENTS}")" && cat >> "${GLOBAL_AGENTS}" <<'EOF'

<!-- GLRP-SKILL-POINTER -->
## Long-running projects

When the user says **activate long running project**, **long-running mode**, or similar,
follow the **`long-running-project`** skill (`/long-running-project`).
EOF
  then
    echo "Updated ${GLOBAL_AGENTS} (pointer)"
  else
    echo "Warning: skill installed, but the optional ${GLOBAL_AGENTS} pointer could not be updated" >&2
  fi
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
