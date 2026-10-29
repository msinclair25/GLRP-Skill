#!/usr/bin/env python3
"""Scaffold long-running project layout into a project root.

Safety defaults:
  - Prefer git repository root over a random nested cwd
  - Refuse $HOME / filesystem root / system temp root unless --allow-unsafe-cwd
  - Never rewrite whole AGENTS.md; only a marked managed section
  - Do not refresh an existing managed section unless --refresh-agents-section
    or --force (your edits outside the markers are always kept)
  - Never overwrite an existing project .grok/config.toml
  - Copy the playbook into the project (never create a machine-local symlink)
  - Other non-state files: skip if present unless --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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


def ensure_file(
    dest: Path,
    src: Path,
    force: bool,
    created: list[str],
    updated: list[str],
    skipped: list[str],
    *,
    update_note: str = "template refreshed",
) -> None:
    exists = dest.exists() or dest.is_symlink()
    if exists and not force:
        skipped.append(str(dest))
        return
    # A forced refresh must replace the link itself, never follow it and write
    # through to a target that may live outside the project.
    if dest.is_symlink():
        dest.unlink()
    write_text(dest, read_text(src))
    if exists:
        updated.append(f"{dest} ({update_note})")
    else:
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
        Path("/tmp").resolve(),
    }
    for variable in ("TMPDIR", "TEMP", "TMP"):
        value = os.environ.get(variable)
        if value:
            unsafe.add(Path(value).resolve())
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


def assert_project_local_parents(root: Path, destinations: list[Path]) -> None:
    """Refuse planned files whose parent symlinks escape the project root."""
    for destination in destinations:
        if destination.is_dir():
            print(
                f"ERROR: expected a file path at {destination}, but found a directory.",
                file=sys.stderr,
            )
            raise SystemExit(3)
        resolved_parent = destination.parent.resolve()
        try:
            resolved_parent.relative_to(root)
        except ValueError:
            print(
                f"ERROR: refusing to write {destination}.\n"
                f"  Its parent resolves outside the project: {resolved_parent}\n"
                "  Replace the parent symlink with a project-local directory, then re-run.",
                file=sys.stderr,
            )
            raise SystemExit(3)


def validated_agents_content(agents_path: Path) -> Optional[tuple[str, int]]:
    """Return existing AGENTS content/count, or None when absent; fail on unsafe layouts."""
    # Following an AGENTS.md symlink can unexpectedly change a shared file or a
    # file outside the repository. Make that choice explicit instead.
    if agents_path.is_symlink():
        print(
            f"ERROR: refusing to modify symlinked {agents_path}.\n"
            "  Replace it with a project-local file, or re-run with --no-agents-merge.",
            file=sys.stderr,
        )
        raise SystemExit(3)

    if not agents_path.exists():
        return None
    if agents_path.is_dir():
        print(
            f"ERROR: expected a file at {agents_path}, but found a directory.",
            file=sys.stderr,
        )
        raise SystemExit(3)

    existing = read_text(agents_path)
    start_count = existing.count(AGENTS_START)
    end_count = existing.count(AGENTS_END)

    # Broken, duplicated, or reversed markers are ambiguous. Do not risk
    # replacing the wrong part of an existing instruction file.
    invalid_markers = (
        start_count != end_count
        or start_count > 1
        or (
            start_count == 1
            and existing.index(AGENTS_START) > existing.index(AGENTS_END)
        )
    )
    if invalid_markers:
        print(
            f"ERROR: {agents_path} has broken or ambiguous LONG-RUNNING-PROJECT markers "
            f"(START={start_count}, END={end_count}).\n"
            "  Keep one ordered START/END pair, or remove all GLRP markers, then re-run.\n"
            "  Tip: restore AGENTS.md from git if the intended layout is unclear.",
            file=sys.stderr,
        )
        raise SystemExit(3)
    return existing, start_count


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
    validated = validated_agents_content(agents_path)

    if validated is None:
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

    existing, start_count = validated

    if start_count == 1:
        if not refresh:
            skipped.append(
                str(agents_path)
                + " (managed LONG-RUNNING-PROJECT section kept as-is; "
                "pass --refresh-agents-section to update template only)"
            )
            return False
        start_at = existing.index(AGENTS_START)
        end_at = existing.index(AGENTS_END, start_at) + len(AGENTS_END)
        new_body = existing[:start_at] + section.strip() + existing[end_at:]
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
    package_json = root / "package.json"
    if package_json.is_file():
        try:
            package_data = json.loads(read_text(package_json))
        except (json.JSONDecodeError, OSError):
            package_data = {}

        scripts = package_data.get("scripts", {}) if isinstance(package_data, dict) else {}
        if not isinstance(scripts, dict):
            scripts = {}

        package_manager = "npm"
        manager_declared = False
        declared_manager = package_data.get("packageManager", "") if isinstance(package_data, dict) else ""
        if isinstance(declared_manager, str):
            candidate = declared_manager.split("@", 1)[0]
            if candidate in {"npm", "pnpm", "yarn", "bun"}:
                package_manager = candidate
                manager_declared = True
        if not manager_declared:
            if (root / "pnpm-lock.yaml").exists():
                package_manager = "pnpm"
            elif (root / "yarn.lock").exists():
                package_manager = "yarn"
            elif (root / "bun.lock").exists() or (root / "bun.lockb").exists():
                package_manager = "bun"

        detected_script = False
        if isinstance(scripts.get("build"), str) and scripts["build"].strip():
            guesses["build"] = f"{package_manager} run build"
            detected_script = True
        if isinstance(scripts.get("test"), str) and scripts["test"].strip():
            guesses["test"] = f"{package_manager} run test"
            detected_script = True
        if isinstance(scripts.get("lint"), str) and scripts["lint"].strip():
            guesses["lint"] = f"{package_manager} run lint"
            detected_script = True
        elif isinstance(scripts.get("typecheck"), str) and scripts["typecheck"].strip():
            guesses["lint"] = f"{package_manager} run typecheck"
            detected_script = True
        # Root package scripts commonly orchestrate mixed-language repos. Once
        # found, do not silently combine them with a different toolchain.
        if detected_script:
            return guesses

    if (root / "Cargo.toml").is_file():
        guesses["build"] = "cargo build"
        guesses["test"] = "cargo test"
        guesses["lint"] = "cargo clippy -- -D warnings"
        return guesses
    if (root / "go.mod").is_file():
        guesses["build"] = "go build ./..."
        guesses["test"] = "go test ./..."
        guesses["lint"] = "go vet ./..."
        return guesses

    pyproject = root / "pyproject.toml"
    pyproject_text = read_text(pyproject).lower() if pyproject.is_file() else ""
    if (
        (root / "pytest.ini").is_file()
        or (root / "conftest.py").is_file()
        or re.search(r"\bpytest\b", pyproject_text)
    ):
        guesses["test"] = "python -m pytest"
    if (
        (root / "ruff.toml").is_file()
        or (root / ".ruff.toml").is_file()
        or re.search(r"\bruff\b", pyproject_text)
    ):
        guesses["lint"] = "python -m ruff check ."
    return guesses


def fill_verify_placeholders(agents_path: Path, guesses: dict[str, str]) -> None:
    if not agents_path.exists():
        return
    text = read_text(agents_path)
    start_at = text.find(AGENTS_START)
    if start_at < 0:
        return
    end_at = text.find(AGENTS_END, start_at)
    if end_at < 0:
        return
    end_at += len(AGENTS_END)

    # Only replace placeholders inside the validated managed block. An identical
    # comment in user-authored content outside the markers must remain untouched.
    managed = text[start_at:end_at]
    placeholders = (
        "<!-- VERIFY_BUILD -->",
        "<!-- VERIFY_TEST -->",
        "<!-- VERIFY_LINT -->",
    )
    if not any(p in managed for p in placeholders):
        return
    managed = managed.replace("<!-- VERIFY_BUILD -->", guesses["build"])
    managed = managed.replace("<!-- VERIFY_TEST -->", guesses["test"])
    managed = managed.replace("<!-- VERIFY_LINT -->", guesses["lint"])
    write_text(agents_path, text[:start_at] + managed + text[end_at:])


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold long-running Grok Build project files")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Starting directory (default: cwd)")
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Overwrite non-state scaffold templates and refresh the managed AGENTS section; "
            "never overwrite an existing .grok/config.toml"
        ),
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
    parser.add_argument(
        "--force-state",
        action="store_true",
        help="Reset SESSION-HANDOFF / FEATURE-LIST / progress.txt templates (destructive)",
    )
    args = parser.parse_args()

    if not TEMPLATES.is_dir():
        print(f"ERROR: templates missing at {TEMPLATES}", file=sys.stderr)
        return 1
    required_templates = [
        SECTION_FILE,
        TEMPLATES / "SESSION-HANDOFF.md",
        TEMPLATES / "FEATURE-LIST.md",
        TEMPLATES / "progress.txt",
        TEMPLATES / "ROADMAP.md",
        TEMPLATES / "DECISIONS.md",
        TEMPLATES / "grok-config.toml",
        TEMPLATES / "project-complete.SKILL.md",
    ] + [
        TEMPLATES / "agents" / name
        for name in (
            "conductor.md",
            "explorer.md",
            "implementer.md",
            "reviewer.md",
        )
    ]
    missing_templates = [path for path in required_templates if not path.is_file()]
    if missing_templates:
        print("ERROR: skill package is incomplete; missing templates:", file=sys.stderr)
        for path in missing_templates:
            print(f"  - {path}", file=sys.stderr)
        return 1
    if not any(path.is_file() for path in PLAYBOOK_CANDIDATES):
        print("ERROR: skill package is incomplete; full PLAYBOOK.md is missing", file=sys.stderr)
        return 1

    root, how = resolve_project_root(args.cwd)
    assert_safe_root(root, args.allow_unsafe_cwd, args.allow_non_git, how)

    # Validate the one existing file we may merge before creating anything, so
    # a broken marker layout or symlink fails without leaving a partial scaffold.
    if not args.no_agents_merge:
        validated_agents_content(root / "AGENTS.md")

    planned_destinations = [
        root / "docs" / "SESSION-HANDOFF.md",
        root / "docs" / "FEATURE-LIST.md",
        root / "docs" / "progress.txt",
        root / "docs" / "ROADMAP.md",
        root / "docs" / "DECISIONS.md",
        root / "docs" / "GROK-LONG-RUNNING-PLAYBOOK.md",
        root / ".grok" / "config.toml",
        root / ".grok" / "skills" / "project-complete" / "SKILL.md",
    ]
    if not args.single_agent:
        planned_destinations.extend(
            root / ".grok" / "agents" / name
            for name in ("conductor.md", "explorer.md", "implementer.md", "reviewer.md")
        )
    assert_project_local_parents(root, planned_destinations)

    created: list[str] = []
    skipped: list[str] = []
    updated: list[str] = []

    # Milestone state: never clobber with --force (progress is precious).
    # Use --force-state to reset deliberately.
    for rel, src in {
        "docs/SESSION-HANDOFF.md": TEMPLATES / "SESSION-HANDOFF.md",
        "docs/FEATURE-LIST.md": TEMPLATES / "FEATURE-LIST.md",
        "docs/progress.txt": TEMPLATES / "progress.txt",
    }.items():
        dest = root / rel
        if rel == "docs/SESSION-HANDOFF.md":
            existed = dest.exists() or dest.is_symlink()
            if existed and not args.force_state:
                skipped.append(str(dest))
            else:
                # A reset replaces a link rather than writing through it, which
                # could otherwise mutate state outside this repository.
                if dest.is_symlink():
                    dest.unlink()
                write_text(dest, stamp_handoff(read_text(src)))
                if existed:
                    updated.append(str(dest) + " (state reset)")
                else:
                    created.append(str(dest))
        else:
            ensure_file(
                dest,
                src,
                args.force_state,
                created,
                updated,
                skipped,
                update_note="state reset",
            )

    for rel, src in {
        "docs/ROADMAP.md": TEMPLATES / "ROADMAP.md",
        "docs/DECISIONS.md": TEMPLATES / "DECISIONS.md",
    }.items():
        ensure_file(root / rel, src, args.force, created, updated, skipped)

    # Project config may contain MCP servers, plugins, or user-authored permission
    # rules. Never replace it wholesale, including under --force.
    project_config = root / ".grok" / "config.toml"
    project_config_existed = project_config.exists() or project_config.is_symlink()
    ensure_file(
        project_config,
        TEMPLATES / "grok-config.toml",
        False,
        created,
        updated,
        skipped,
    )

    if not args.single_agent:
        for name in ("conductor.md", "explorer.md", "implementer.md", "reviewer.md"):
            ensure_file(
                root / ".grok" / "agents" / name,
                TEMPLATES / "agents" / name,
                args.force,
                created,
                updated,
                skipped,
            )

    ensure_file(
        root / ".grok" / "skills" / "project-complete" / "SKILL.md",
        TEMPLATES / "project-complete.SKILL.md",
        args.force,
        created,
        updated,
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

    playbook_copy = root / "docs" / "GROK-LONG-RUNNING-PLAYBOOK.md"
    for cand in PLAYBOOK_CANDIDATES:
        if not cand.is_file():
            continue
        exists = playbook_copy.exists() or playbook_copy.is_symlink()
        if exists and not args.force:
            skipped.append(str(playbook_copy))
            break
        if playbook_copy.is_symlink():
            playbook_copy.unlink()
        write_text(playbook_copy, read_text(cand))
        if exists:
            updated.append(str(playbook_copy) + " (portable copy refreshed)")
        else:
            created.append(str(playbook_copy) + " (portable copy)")
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
    print("  - Existing .grok/config.toml is never overwritten, including with --force.")
    print("\nProject config:")
    if project_config_existed:
        print("  - Existing .grok/config.toml was kept unchanged.")
        print("  - GLRP deny rules were NOT merged automatically; compare your config with:")
        print(f"    {TEMPLATES / 'grok-config.toml'}")
    else:
        print("  - Created .grok/config.toml with GLRP's recommended destructive-command denies.")
    grok_home_value = os.environ.get("GROK_HOME")
    grok_home = Path(grok_home_value).expanduser() if grok_home_value else Path.home() / ".grok"
    print("\nMemory (NOT enabled by this scaffold):")
    print(f"  - Persistent: [memory] enabled = true in {grok_home / 'config.toml'}")
    print("  - One session: GROK_MEMORY=1 grok")
    print("  - Mid-session: open /memory and press t to toggle")
    print("\nActivation:")
    print("  - Review the diff, then start a new Grok session in this project.")
    print("  - Grant folder trust when prompted (or launch from the project with grok --trust).")
    print("  - Project AGENTS.md/config are loaded at session start after trust.")
    print("\nNext:")
    print("  1. Confirm you are in the right project root (above).")
    print("  2. Edit AGENTS.md verify commands if still <FILL:…>")
    print("  3. Fill docs/FEATURE-LIST.md and SESSION-HANDOFF.md")
    print("  4. Restart in a trusted session, then work from explicit checklists")
    print("  5. Run project verify commands and /project-complete before declaring done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
