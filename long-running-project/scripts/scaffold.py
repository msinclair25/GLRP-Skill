#!/usr/bin/env python3
"""Scaffold long-running project layout into the current working directory.

Idempotent: existing files are left alone unless --force (agents/config always
safe-merge for AGENTS.md managed section).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "references" / "templates"

AGENTS_START = "<!-- LONG-RUNNING-PROJECT:START -->"
AGENTS_END = "<!-- LONG-RUNNING-PROJECT:END -->"
SECTION_FILE = TEMPLATES / "AGENTS.section.md"

# Playbook path (optional deep reference for humans)
PLAYBOOK_CANDIDATES = [
    SKILL_ROOT.parent / "docs" / "PLAYBOOK.md",  # when installed from GLRP-Skill repo
    SKILL_ROOT / "docs" / "PLAYBOOK.md",
    Path.home() / "Documents" / "CodexSolLunaRoleKit" / "Grok Build - Long Running Project Playbook.md",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_file(dest: Path, src: Path, force: bool, created: list[str], skipped: list[str]) -> None:
    if dest.exists() and not force:
        skipped.append(str(dest))
        return
    write_text(dest, read_text(src))
    created.append(str(dest))


def merge_agents_section(agents_path: Path, force_section: bool, created: list[str], updated: list[str]) -> None:
    section = read_text(SECTION_FILE).strip() + "\n"
    if not agents_path.exists():
        header = (
            "# Project agent rules\n\n"
            "Shared rules for all agents. Role-specific behavior lives under `.grok/agents/`.\n\n"
        )
        write_text(agents_path, header + section)
        created.append(str(agents_path))
        return

    existing = read_text(agents_path)
    if AGENTS_START in existing and AGENTS_END in existing:
        if not force_section and "LONG-RUNNING-PROJECT:START" in existing:
            # Refresh managed section content always (templates improve over time)
            pattern = re.compile(
                re.escape(AGENTS_START) + r".*?" + re.escape(AGENTS_END),
                re.DOTALL,
            )
            new_body = pattern.sub(section.strip(), existing)
            if new_body != existing:
                write_text(agents_path, new_body if new_body.endswith("\n") else new_body + "\n")
                updated.append(str(agents_path) + " (managed section refreshed)")
            else:
                updated.append(str(agents_path) + " (managed section unchanged)")
            return
        pattern = re.compile(
            re.escape(AGENTS_START) + r".*?" + re.escape(AGENTS_END),
            re.DOTALL,
        )
        new_body = pattern.sub(section.strip(), existing)
        write_text(agents_path, new_body if new_body.endswith("\n") else new_body + "\n")
        updated.append(str(agents_path) + " (managed section refreshed)")
        return

    # Append managed section
    sep = "" if existing.endswith("\n") else "\n"
    write_text(agents_path, existing + sep + "\n" + section)
    updated.append(str(agents_path) + " (managed section appended)")


def stamp_handoff(content: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return content.replace("<!-- DATE -->", now)


def detect_verify_commands(root: Path) -> dict[str, str]:
    """Best-effort guess of build/test/lint commands."""
    guesses: dict[str, str] = {
        "build": "<FILL: e.g. npm run build | cargo build | go build ./...>",
        "test": "<FILL: e.g. npm test | cargo test | pytest | go test ./...>",
        "lint": "<FILL: e.g. npm run lint | cargo clippy | ruff check .>",
    }
    if (root / "package.json").exists():
        pkg = read_text(root / "package.json")
        if '"build"' in pkg:
            guesses["build"] = "npm run build"
        if '"test"' in pkg:
            guesses["test"] = "npm test"
        if '"lint"' in pkg:
            guesses["lint"] = "npm run lint"
        elif '"typecheck"' in pkg:
            guesses["lint"] = "npm run typecheck"
    if (root / "Cargo.toml").exists():
        guesses["build"] = "cargo build"
        guesses["test"] = "cargo test"
        guesses["lint"] = "cargo clippy -- -D warnings"
    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists():
        guesses["test"] = "pytest"
        guesses["lint"] = "ruff check .  # or: python -m ruff check ."
    if (root / "go.mod").exists():
        guesses["build"] = "go build ./..."
        guesses["test"] = "go test ./..."
        guesses["lint"] = "go vet ./..."
    return guesses


def fill_verify_placeholders(agents_path: Path, guesses: dict[str, str]) -> None:
    if not agents_path.exists():
        return
    text = read_text(agents_path)
    text = text.replace("<!-- VERIFY_BUILD -->", guesses["build"])
    text = text.replace("<!-- VERIFY_TEST -->", guesses["test"])
    text = text.replace("<!-- VERIFY_LINT -->", guesses["lint"])
    write_text(agents_path, text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold long-running Grok Build project files")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Project root (default: cwd)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-AGENTS template files",
    )
    parser.add_argument(
        "--single-agent",
        action="store_true",
        help="Skip .grok/agents/* multi-agent profiles",
    )
    parser.add_argument(
        "--no-agents-merge",
        action="store_true",
        help="Do not create or update AGENTS.md",
    )
    args = parser.parse_args()
    root: Path = args.cwd.resolve()

    if not TEMPLATES.is_dir():
        print(f"ERROR: templates missing at {TEMPLATES}", file=sys.stderr)
        return 1

    created: list[str] = []
    skipped: list[str] = []
    updated: list[str] = []

    # docs/*
    docs = {
        "docs/SESSION-HANDOFF.md": TEMPLATES / "SESSION-HANDOFF.md",
        "docs/FEATURE-LIST.md": TEMPLATES / "FEATURE-LIST.md",
        "docs/progress.txt": TEMPLATES / "progress.txt",
        "docs/ROADMAP.md": TEMPLATES / "ROADMAP.md",
        "docs/DECISIONS.md": TEMPLATES / "DECISIONS.md",
    }
    for rel, src in docs.items():
        dest = root / rel
        if rel == "docs/SESSION-HANDOFF.md" and (not dest.exists() or args.force):
            write_text(dest, stamp_handoff(read_text(src)))
            created.append(str(dest))
        else:
            ensure_file(dest, src, args.force, created, skipped)

    # .grok/config.toml
    ensure_file(
        root / ".grok" / "config.toml",
        TEMPLATES / "grok-config.toml",
        args.force,
        created,
        skipped,
    )

    # multi-agent profiles
    if not args.single_agent:
        for name in ("conductor.md", "explorer.md", "implementer.md", "reviewer.md"):
            ensure_file(
                root / ".grok" / "agents" / name,
                TEMPLATES / "agents" / name,
                args.force,
                created,
                skipped,
            )

    # project-complete skill
    ensure_file(
        root / ".grok" / "skills" / "project-complete" / "SKILL.md",
        TEMPLATES / "project-complete.SKILL.md",
        args.force,
        created,
        skipped,
    )

    # AGENTS.md managed section
    if not args.no_agents_merge:
        agents_path = root / "AGENTS.md"
        merge_agents_section(agents_path, force_section=True, created=created, updated=updated)
        fill_verify_placeholders(agents_path, detect_verify_commands(root))

    # Optional pointer to full playbook for humans
    playbook_link = root / "docs" / "GROK-LONG-RUNNING-PLAYBOOK.md"
    for cand in PLAYBOOK_CANDIDATES:
        if cand.is_file() and (not playbook_link.exists() or args.force):
            try:
                if playbook_link.exists() or playbook_link.is_symlink():
                    playbook_link.unlink()
                playbook_link.symlink_to(cand)
                created.append(f"{playbook_link} -> {cand}")
            except OSError:
                # Fallback: short pointer file
                write_text(
                    playbook_link,
                    f"# Long-running playbook\n\nFull guide: `{cand}`\n\n"
                    f"Or user skill templates under `{SKILL_ROOT}`.\n",
                )
                created.append(str(playbook_link) + " (pointer file)")
            break

    # Summary
    print("## Long-running project scaffold")
    print(f"Root: {root}")
    print(f"\nCreated ({len(created)}):")
    for p in created:
        print(f"  + {p}")
    print(f"\nUpdated ({len(updated)}):")
    for p in updated:
        print(f"  ~ {p}")
    print(f"\nSkipped existing ({len(skipped)}):")
    for p in skipped:
        print(f"  = {p}")
    print("\nNext:")
    print("  1. Edit AGENTS.md verify commands if still <FILL:…>")
    print("  2. Fill docs/FEATURE-LIST.md and SESSION-HANDOFF.md for the current milestone")
    print("  3. If using project hooks/MCP later: /hooks-trust or grok --trust")
    print("  4. Enable memory if desired: /memory on  (or GROK_MEMORY=1)")
    print("  5. Start work with a checklist prompt; /check-work after multi-part tasks")
    print("  6. Deep reference: docs/GROK-LONG-RUNNING-PLAYBOOK.md or the user skill README")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
