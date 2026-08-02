#!/usr/bin/env python3
"""Scaffold long-running project layout into a project root.

Safety defaults:
  - Prefer git repository root over a random nested cwd
  - Refuse $HOME / filesystem root unless --allow-unsafe-cwd
  - Never rewrite whole AGENTS.md; only a marked managed section
  - Do not refresh an existing managed section unless --refresh-agents-section
    or --force (your edits outside the markers are always kept)
  - Other files: skip if present unless --force
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "references" / "templates"

AGENTS_START = "<!-- LONG-RUNNING-PROJECT:START -->"
AGENTS_END = "<!-- LONG-RUNNING-PROJECT:END -->"
SECTION_FILE = TEMPLATES / "AGENTS.section.md"

PLAYBOOK_CANDIDATES = [
    SKILL_ROOT.parent / "docs" / "PLAYBOOK.md",
    SKILL_ROOT / "docs" / "PLAYBOOK.md",
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


def resolve_project_root(cwd: Path) -> tuple[Path, str]:
    """Return (root, how_resolved). Prefer git toplevel containing cwd."""
    cwd = cwd.resolve()
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        root = Path(out.stdout.strip()).resolve()
        return root, "git-toplevel"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return cwd, "cwd-no-git"


def assert_safe_root(root: Path, allow_unsafe: bool, allow_non_git: bool, how: str) -> None:
    home = Path.home().resolve()
    unsafe = {
        home,
        Path("/").resolve(),
        Path(os.environ.get("TMPDIR", "/tmp")).resolve(),
    }
    # Also common Windows user profile style
    if root in unsafe or root == home:
        if not allow_unsafe:
            print(
                f"ERROR: refusing to scaffold in {root}\n"
                "  That looks like home or a temp/root path, not a project.\n"
                "  cd into your project (git repo) and re-run, or pass\n"
                "  --cwd /path/to/repo --allow-unsafe-cwd if you really mean it.",
                file=sys.stderr,
            )
            raise SystemExit(2)

    if how == "cwd-no-git" and not allow_non_git:
        print(
            f"ERROR: {root} is not inside a git repository.\n"
            "  Activate from a project with `git` initialized so we use the repo root.\n"
            "  Or pass --allow-non-git if this folder is intentionally not a git repo.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # Nested path: user passed a subdir but we resolved to git root — that's OK (informational)
    print(f"Project root: {root} ({how})")


def merge_agents_section(
    agents_path: Path,
    *,
    refresh: bool,
    created: list[str],
    updated: list[str],
    skipped: list[str],
) -> bool:
    """Merge managed section. Returns True if file was written (so verify fill may run)."""
    section = read_text(SECTION_FILE).strip() + "\n"

    if not agents_path.exists():
        header = (
            "# Project agent rules\n\n"
            "Shared rules for all agents. Role-specific behavior lives under `.grok/agents/`.\n\n"
            "The block between LONG-RUNNING-PROJECT markers is managed by the GLRP skill.\n"
            "Edit freely **outside** those markers. Re-activate with `--refresh-agents-section`\n"
            "only when you want the managed block updated from the skill template.\n\n"
        )
        write_text(agents_path, header + section)
        created.append(str(agents_path))
        return True

    existing = read_text(agents_path)

    if AGENTS_START in existing and AGENTS_END in existing:
        if not refresh:
            skipped.append(
                str(agents_path)
                + " (managed LONG-RUNNING-PROJECT section kept as-is; "
                "pass --refresh-agents-section to update template only)"
            )
            return False
        pattern = re.compile(
            re.escape(AGENTS_START) + r".*?" + re.escape(AGENTS_END),
            re.DOTALL,
        )
        new_body = pattern.sub(section.strip(), existing)
        write_text(agents_path, new_body if new_body.endswith("\n") else new_body + "\n")
        updated.append(str(agents_path) + " (managed section refreshed; content outside markers preserved)")
        return True

    # No markers: append only — never rewrite the rest of the file
    sep = "" if existing.endswith("\n") else "\n"
    write_text(agents_path, existing + sep + "\n" + section)
    updated.append(str(agents_path) + " (managed section appended; existing content unchanged)")
    return True


def stamp_handoff(content: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return content.replace("<!-- DATE -->", now)


def detect_verify_commands(root: Path) -> dict[str, str]:
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
    # Only replace HTML placeholders still present (never clobber user-edited commands)
    if "<!-- VERIFY_BUILD -->" not in text and "<!-- VERIFY_TEST -->" not in text:
        return
    text = text.replace("<!-- VERIFY_BUILD -->", guesses["build"])
    text = text.replace("<!-- VERIFY_TEST -->", guesses["test"])
    text = text.replace("<!-- VERIFY_LINT -->", guesses["lint"])
    write_text(agents_path, text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold long-running Grok Build project files")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Starting directory (default: cwd)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-AGENTS scaffold files; also refresh managed AGENTS section",
    )
    parser.add_argument(
        "--refresh-agents-section",
        action="store_true",
        help="Replace only the LONG-RUNNING-PROJECT managed block in AGENTS.md (keep rest of file)",
    )
    parser.add_argument(
        "--single-agent",
        action="store_true",
        help="Skip .grok/agents/* multi-agent profiles",
    )
    parser.add_argument(
        "--no-agents-merge",
        action="store_true",
        help="Do not create or update AGENTS.md at all",
    )
    parser.add_argument(
        "--allow-non-git",
        action="store_true",
        help="Allow scaffolding outside a git repository",
    )
    parser.add_argument(
        "--allow-unsafe-cwd",
        action="store_true",
        help="Allow scaffolding in $HOME or temp/root (not recommended)",
    )
    args = parser.parse_args()

    if not TEMPLATES.is_dir():
        print(f"ERROR: templates missing at {TEMPLATES}", file=sys.stderr)
        return 1

    root, how = resolve_project_root(args.cwd)
    assert_safe_root(root, args.allow_unsafe_cwd, args.allow_non_git, how)

    created: list[str] = []
    skipped: list[str] = []
    updated: list[str] = []

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

    ensure_file(
        root / ".grok" / "config.toml",
        TEMPLATES / "grok-config.toml",
        args.force,
        created,
        skipped,
    )

    if not args.single_agent:
        for name in ("conductor.md", "explorer.md", "implementer.md", "reviewer.md"):
            ensure_file(
                root / ".grok" / "agents" / name,
                TEMPLATES / "agents" / name,
                args.force,
                created,
                skipped,
            )

    ensure_file(
        root / ".grok" / "skills" / "project-complete" / "SKILL.md",
        TEMPLATES / "project-complete.SKILL.md",
        args.force,
        created,
        skipped,
    )

    if not args.no_agents_merge:
        agents_path = root / "AGENTS.md"
        refresh = args.refresh_agents_section or args.force
        wrote = merge_agents_section(
            agents_path,
            refresh=refresh,
            created=created,
            updated=updated,
            skipped=skipped,
        )
        if wrote:
            fill_verify_placeholders(agents_path, detect_verify_commands(root))

    playbook_link = root / "docs" / "GROK-LONG-RUNNING-PLAYBOOK.md"
    for cand in PLAYBOOK_CANDIDATES:
        if cand.is_file() and (not playbook_link.exists() or args.force):
            try:
                if playbook_link.exists() or playbook_link.is_symlink():
                    playbook_link.unlink()
                playbook_link.symlink_to(cand)
                created.append(f"{playbook_link} -> {cand}")
            except OSError:
                write_text(
                    playbook_link,
                    f"# Long-running playbook\n\nFull guide: `{cand}`\n\n"
                    f"Skill root: `{SKILL_ROOT}`\n",
                )
                created.append(str(playbook_link) + " (pointer file)")
            break

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
    print("\nAGENTS.md safety:")
    print("  - Your content outside LONG-RUNNING-PROJECT markers is never rewritten.")
    print("  - Existing managed section is left alone unless --refresh-agents-section or --force.")
    print("\nMemory (NOT enabled by this scaffold):")
    print("  - Optional: grok --experimental-memory   or   export GROK_MEMORY=1")
    print("  - Or: [memory] enabled = true in ~/.grok/config.toml   or   /memory on")
    print("\nNext:")
    print("  1. Confirm you are in the right project root (above).")
    print("  2. Edit AGENTS.md verify commands if still <FILL:…>")
    print("  3. Fill docs/FEATURE-LIST.md and SESSION-HANDOFF.md")
    print("  4. Start work with a checklist prompt; /check-work after multi-part tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
