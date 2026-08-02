#!/usr/bin/env python3
"""Tests for long-running-project/scripts/scaffold.py"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "long-running-project" / "scripts" / "scaffold.py"


def load_scaffold():
    spec = importlib.util.spec_from_file_location("glrp_scaffold", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sc = load_scaffold()


def git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    # identity for any future commits in tests
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True)


def run_scaffold(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


class ScaffoldSafetyTests(unittest.TestCase):
    def test_refuses_home(self) -> None:
        r = run_scaffold(["--cwd", str(Path.home())])
        self.assertEqual(r.returncode, 2)
        self.assertIn("refusing", r.stderr.lower())

    def test_refuses_non_git_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            r = run_scaffold(["--cwd", tmp])
            self.assertEqual(r.returncode, 2)
            self.assertIn("git", r.stderr.lower())

    def test_allows_non_git_with_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # still unsafe if tmp equals TMPDIR exactly — use subdir
            root = Path(tmp) / "proj"
            root.mkdir()
            r = run_scaffold(["--cwd", str(root), "--allow-non-git", "--allow-unsafe-cwd"])
            # may still refuse if root is under weird paths; allow-unsafe should pass
            if Path(tmp).resolve() == Path(os.environ.get("TMPDIR", "/tmp")).resolve():
                # parent is TMPDIR; child should be OK without allow-unsafe for TMPDIR exact match only
                r = run_scaffold(["--cwd", str(root), "--allow-non-git"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((root / "AGENTS.md").is_file())


class ScaffoldHappyPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        git_init(self.root)

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_creates_expected_layout(self) -> None:
        r = run_scaffold(["--cwd", str(self.root)])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        for rel in (
            "AGENTS.md",
            "docs/SESSION-HANDOFF.md",
            "docs/FEATURE-LIST.md",
            "docs/progress.txt",
            "docs/ROADMAP.md",
            "docs/DECISIONS.md",
            ".grok/config.toml",
            ".grok/agents/conductor.md",
            ".grok/agents/explorer.md",
            ".grok/agents/implementer.md",
            ".grok/agents/reviewer.md",
            ".grok/skills/project-complete/SKILL.md",
        ):
            self.assertTrue((self.root / rel).is_file(), rel)
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("<!-- LONG-RUNNING-PROJECT:START -->", text)
        self.assertIn("<!-- LONG-RUNNING-PROJECT:END -->", text)

    def test_single_agent_skips_agent_profiles(self) -> None:
        r = run_scaffold(["--cwd", str(self.root), "--single-agent"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.root / ".grok" / "agents" / "conductor.md").exists())
        self.assertTrue((self.root / "AGENTS.md").is_file())

    def test_second_run_skips_existing_and_keeps_agents_section(self) -> None:
        self.assertEqual(run_scaffold(["--cwd", str(self.root)]).returncode, 0)
        custom = "\n## My custom rules\n- keep forever\n"
        agents = self.root / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8") + custom, encoding="utf-8")
        (self.root / "docs" / "SESSION-HANDOFF.md").write_text("USER STATE\n", encoding="utf-8")

        r = run_scaffold(["--cwd", str(self.root)])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("kept as-is", r.stdout)
        self.assertIn("keep forever", agents.read_text(encoding="utf-8"))
        self.assertEqual((self.root / "docs" / "SESSION-HANDOFF.md").read_text(encoding="utf-8"), "USER STATE\n")

    def test_no_agents_merge(self) -> None:
        r = run_scaffold(["--cwd", str(self.root), "--no-agents-merge"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertTrue((self.root / "docs" / "FEATURE-LIST.md").is_file())


class AgentsMergeTests(unittest.TestCase):
    def test_broken_markers_exit_3(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_init(root)
            (root / "AGENTS.md").write_text(
                "# Hi\n<!-- LONG-RUNNING-PROJECT:START -->\npartial only\n",
                encoding="utf-8",
            )
            r = run_scaffold(["--cwd", str(root)])
            self.assertEqual(r.returncode, 3)
            self.assertIn("broken", r.stderr.lower())
            text = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(text.count("LONG-RUNNING-PROJECT:START"), 1)

    def test_append_when_no_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_init(root)
            (root / "AGENTS.md").write_text("# Existing\n\nKeep me.\n", encoding="utf-8")
            r = run_scaffold(["--cwd", str(root)])
            self.assertEqual(r.returncode, 0, r.stderr)
            text = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Existing"))
            self.assertIn("Keep me.", text)
            self.assertIn("<!-- LONG-RUNNING-PROJECT:START -->", text)

    def test_refresh_only_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_init(root)
            self.assertEqual(run_scaffold(["--cwd", str(root)]).returncode, 0)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8") + "\n## Outside\n- stay\n",
                encoding="utf-8",
            )
            # mutate inside markers
            text = agents.read_text(encoding="utf-8")
            text = text.replace("Test ratchet", "TEST_RATCHET_MUTATED")
            agents.write_text(text, encoding="utf-8")

            r = run_scaffold(["--cwd", str(root), "--refresh-agents-section"])
            self.assertEqual(r.returncode, 0, r.stderr)
            final = agents.read_text(encoding="utf-8")
            self.assertIn("## Outside", final)
            self.assertIn("- stay", final)
            self.assertNotIn("TEST_RATCHET_MUTATED", final)
            self.assertIn("Test ratchet", final)


class VerifyPlaceholderTests(unittest.TestCase):
    def test_fills_lint_only_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "AGENTS.md"
            p.write_text("Lint: `<!-- VERIFY_LINT -->`\n", encoding="utf-8")
            sc.fill_verify_placeholders(
                p, {"build": "B", "test": "T", "lint": "LINTCMD"}
            )
            text = p.read_text(encoding="utf-8")
            self.assertIn("LINTCMD", text)
            self.assertNotIn("VERIFY_LINT", text)

    def test_does_not_clobber_user_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "AGENTS.md"
            p.write_text("Build: `npm run build`\nTest: `npm test`\n", encoding="utf-8")
            before = p.read_text(encoding="utf-8")
            sc.fill_verify_placeholders(
                p, {"build": "NOPE", "test": "NOPE", "lint": "NOPE"}
            )
            self.assertEqual(p.read_text(encoding="utf-8"), before)


class ForceBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        git_init(self.root)
        self.assertEqual(run_scaffold(["--cwd", str(self.root)]).returncode, 0)

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_force_preserves_handoff(self) -> None:
        handoff = self.root / "docs" / "SESSION-HANDOFF.md"
        handoff.write_text("USER IMPORTANT STATE\n", encoding="utf-8")
        r = run_scaffold(["--cwd", str(self.root), "--force"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(handoff.read_text(encoding="utf-8"), "USER IMPORTANT STATE\n")

    def test_force_state_resets_handoff(self) -> None:
        handoff = self.root / "docs" / "SESSION-HANDOFF.md"
        handoff.write_text("USER IMPORTANT STATE\n", encoding="utf-8")
        r = run_scaffold(["--cwd", str(self.root), "--force-state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        text = handoff.read_text(encoding="utf-8")
        self.assertNotEqual(text, "USER IMPORTANT STATE\n")
        self.assertIn("STATUS", text)

    def test_force_overwrites_agent_profile(self) -> None:
        agent = self.root / ".grok" / "agents" / "conductor.md"
        agent.write_text("CUSTOM\n", encoding="utf-8")
        r = run_scaffold(["--cwd", str(self.root), "--force"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(agent.read_text(encoding="utf-8"), "CUSTOM\n")
        self.assertIn("conductor", agent.read_text(encoding="utf-8"))


class TemplateIntegrityTests(unittest.TestCase):
    def test_agents_section_has_markers_and_placeholders(self) -> None:
        sec = (
            REPO_ROOT
            / "long-running-project"
            / "references"
            / "templates"
            / "AGENTS.section.md"
        ).read_text(encoding="utf-8")
        self.assertIn("<!-- LONG-RUNNING-PROJECT:START -->", sec)
        self.assertIn("<!-- LONG-RUNNING-PROJECT:END -->", sec)
        for ph in ("VERIFY_BUILD", "VERIFY_TEST", "VERIFY_LINT"):
            self.assertIn(ph, sec)

    def test_skill_md_exists(self) -> None:
        self.assertTrue((REPO_ROOT / "long-running-project" / "SKILL.md").is_file())
        self.assertTrue(SCRIPT.is_file())


if __name__ == "__main__":
    unittest.main()
