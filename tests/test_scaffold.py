#!/usr/bin/env python3
"""Tests for long-running-project/scripts/scaffold.py"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "long-running-project" / "scripts" / "scaffold.py"
INSTALL = REPO_ROOT / "install.sh"


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


def run_scaffold(args: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def run_install(grok_home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GROK_HOME"] = str(grok_home)
    return subprocess.run(
        ["bash", str(INSTALL)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )


class InstallerTests(unittest.TestCase):
    def test_installs_grok_47_skill_idempotently_and_preserves_global_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            grok_home = Path(tmp) / "Grok Home"
            grok_home.mkdir()
            global_agents = grok_home / "AGENTS.md"
            global_agents.write_text(
                "# User rules\n\nKeep me. A sentence may mention long-running-project.\n",
                encoding="utf-8",
            )

            first = run_install(grok_home)
            second = run_install(grok_home)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)

            installed = grok_home / "skills" / "long-running-project"
            self.assertTrue((installed / "SKILL.md").is_file())
            playbook = (installed / "docs" / "PLAYBOOK.md").read_text(encoding="utf-8")
            self.assertIn("Grok 4.7", playbook)

            agents = global_agents.read_text(encoding="utf-8")
            self.assertIn("Keep me.", agents)
            self.assertEqual(agents.count("## Long-running projects"), 1)
            self.assertEqual(agents.count("<!-- GLRP-SKILL-POINTER -->"), 1)
            self.assertEqual(list((grok_home / "skills").glob(".glrp-install.*")), [])

    def test_installer_does_not_follow_global_agents_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            grok_home = base / "grok-home"
            grok_home.mkdir()
            target = base / "shared-agents.md"
            target.write_text("SHARED RULES\n", encoding="utf-8")
            (grok_home / "AGENTS.md").symlink_to(target)

            result = run_install(grok_home)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("file is a symlink", result.stdout)
            self.assertEqual(target.read_text(encoding="utf-8"), "SHARED RULES\n")
            self.assertTrue(
                (grok_home / "skills" / "long-running-project" / "SKILL.md").is_file()
            )

    def test_installer_succeeds_when_optional_agents_pointer_cannot_be_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            grok_home = Path(tmp) / "grok-home"
            (grok_home / "AGENTS.md").mkdir(parents=True)

            result = run_install(grok_home)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("optional", result.stderr)
            self.assertTrue(
                (grok_home / "skills" / "long-running-project" / "SKILL.md").is_file()
            )

    def test_installer_reports_missing_home_cleanly(self) -> None:
        env = os.environ.copy()
        env.pop("HOME", None)
        env.pop("GROK_HOME", None)

        result = subprocess.run(
            ["bash", str(INSTALL)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=env,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("neither GROK_HOME nor HOME", result.stderr)

    def test_installer_recognizes_legacy_pointer_without_duplication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            grok_home = Path(tmp) / "grok-home"
            grok_home.mkdir()
            agents = grok_home / "AGENTS.md"
            agents.write_text(
                "## Long-running projects\n\n"
                "follow the **`long-running-project`** skill (`/long-running-project`).\n",
                encoding="utf-8",
            )

            result = run_install(grok_home)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            text = agents.read_text(encoding="utf-8")
            self.assertEqual(text.count("## Long-running projects"), 1)

    def test_installed_skill_package_can_scaffold_a_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            grok_home = base / "grok home"
            repo = base / "project"
            grok_home.mkdir()
            repo.mkdir()
            git_init(repo)
            install = run_install(grok_home)
            self.assertEqual(install.returncode, 0, install.stderr + install.stdout)

            installed_script = (
                grok_home
                / "skills"
                / "long-running-project"
                / "scripts"
                / "scaffold.py"
            )
            result = subprocess.run(
                ["python3", str(installed_script), "--cwd", str(repo)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue((repo / "AGENTS.md").is_file())
            self.assertTrue((repo / ".grok" / "config.toml").is_file())
            self.assertIn(
                "Grok 4.7",
                (repo / "docs" / "GROK-LONG-RUNNING-PLAYBOOK.md").read_text(
                    encoding="utf-8"
                ),
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

    def test_refuses_docs_parent_symlink_outside_project_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            outside = base / "shared-docs"
            root.mkdir()
            outside.mkdir()
            git_init(root)
            (root / "docs").symlink_to(outside, target_is_directory=True)

            r = run_scaffold(["--cwd", str(root)])

            self.assertEqual(r.returncode, 3)
            self.assertIn("outside the project", r.stderr)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse((root / ".grok").exists())

    def test_refuses_nested_grok_parent_symlink_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            outside = base / "shared-agents"
            root.mkdir()
            outside.mkdir()
            git_init(root)
            (root / ".grok").mkdir()
            (root / ".grok" / "agents").symlink_to(outside, target_is_directory=True)

            r = run_scaffold(["--cwd", str(root)])

            self.assertEqual(r.returncode, 3)
            self.assertIn("outside the project", r.stderr)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse((root / "docs").exists())

    def test_refuses_directory_where_scaffold_file_should_be(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_init(root)
            (root / "docs" / "FEATURE-LIST.md").mkdir(parents=True)

            r = run_scaffold(["--cwd", str(root)])

            self.assertEqual(r.returncode, 3)
            self.assertIn("expected a file path", r.stderr)
            self.assertFalse((root / ".grok").exists())
            self.assertFalse((root / "docs" / "SESSION-HANDOFF.md").exists())


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
            "docs/GROK-LONG-RUNNING-PLAYBOOK.md",
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
        playbook = self.root / "docs" / "GROK-LONG-RUNNING-PLAYBOOK.md"
        self.assertFalse(playbook.is_symlink())
        self.assertIn("Grok 4.7", playbook.read_text(encoding="utf-8"))
        self.assertIn("new Grok session", r.stdout)
        self.assertIn("folder trust", r.stdout)

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

    def test_duplicate_markers_exit_3_without_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_init(root)
            agents = root / "AGENTS.md"
            original = (
                "# Hi\n"
                "<!-- LONG-RUNNING-PROJECT:START -->\none\n"
                "<!-- LONG-RUNNING-PROJECT:END -->\n"
                "<!-- LONG-RUNNING-PROJECT:START -->\ntwo\n"
                "<!-- LONG-RUNNING-PROJECT:END -->\n"
            )
            agents.write_text(original, encoding="utf-8")

            r = run_scaffold(["--cwd", str(root), "--refresh-agents-section"])

            self.assertEqual(r.returncode, 3)
            self.assertIn("ambiguous", r.stderr.lower())
            self.assertEqual(agents.read_text(encoding="utf-8"), original)
            self.assertFalse((root / ".grok").exists())

    def test_reversed_markers_exit_3_without_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_init(root)
            agents = root / "AGENTS.md"
            original = (
                "# Hi\n<!-- LONG-RUNNING-PROJECT:END -->\n"
                "body\n<!-- LONG-RUNNING-PROJECT:START -->\n"
            )
            agents.write_text(original, encoding="utf-8")

            r = run_scaffold(["--cwd", str(root), "--refresh-agents-section"])

            self.assertEqual(r.returncode, 3)
            self.assertIn("broken", r.stderr.lower())
            self.assertEqual(agents.read_text(encoding="utf-8"), original)

    def test_symlinked_agents_file_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git_init(root)
            target = root / "shared-agents.md"
            target.write_text("DO NOT TOUCH\n", encoding="utf-8")
            (root / "AGENTS.md").symlink_to(target)

            r = run_scaffold(["--cwd", str(root)])

            self.assertEqual(r.returncode, 3)
            self.assertIn("symlinked", r.stderr.lower())
            self.assertEqual(target.read_text(encoding="utf-8"), "DO NOT TOUCH\n")
            self.assertFalse((root / ".grok").exists())

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
            p.write_text(
                f"{sc.AGENTS_START}\nLint: `<!-- VERIFY_LINT -->`\n{sc.AGENTS_END}\n",
                encoding="utf-8",
            )
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

    def test_does_not_replace_placeholder_outside_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "AGENTS.md"
            outside = "Outside: <!-- VERIFY_TEST -->"
            p.write_text(
                f"{outside}\n{sc.AGENTS_START}\n"
                "Inside: <!-- VERIFY_TEST -->\n"
                f"{sc.AGENTS_END}\n",
                encoding="utf-8",
            )

            sc.fill_verify_placeholders(
                p, {"build": "B", "test": "TESTCMD", "lint": "L"}
            )

            text = p.read_text(encoding="utf-8")
            self.assertIn(outside, text)
            self.assertIn("Inside: TESTCMD", text)

    def test_package_scripts_use_declared_package_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                '{"packageManager":"pnpm@10.0.0","scripts":'
                '{"build":"vite build","test":"vitest","typecheck":"tsc"}}\n',
                encoding="utf-8",
            )
            (root / "yarn.lock").write_text("stale lock\n", encoding="utf-8")

            guesses = sc.detect_verify_commands(root)

            self.assertEqual(guesses["build"], "pnpm run build")
            self.assertEqual(guesses["test"], "pnpm run test")
            self.assertEqual(guesses["lint"], "pnpm run typecheck")

    def test_root_package_scripts_are_not_mixed_with_other_toolchains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                '{"scripts":{"test":"vitest"}}\n', encoding="utf-8"
            )
            (root / "Cargo.toml").write_text("[package]\nname = 'also-rust'\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                '[project.optional-dependencies]\ndev = ["pytest", "ruff"]\n',
                encoding="utf-8",
            )

            guesses = sc.detect_verify_commands(root)

            self.assertEqual(guesses["test"], "npm run test")
            self.assertTrue(guesses["build"].startswith("<FILL:"))
            self.assertTrue(guesses["lint"].startswith("<FILL:"))

    def test_package_detection_only_reads_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                '{"dependencies":{"test":"1.0.0","build":"1.0.0"}}\n',
                encoding="utf-8",
            )

            guesses = sc.detect_verify_commands(root)

            self.assertTrue(guesses["build"].startswith("<FILL:"))
            self.assertTrue(guesses["test"].startswith("<FILL:"))

    def test_package_detection_ignores_empty_or_non_string_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                '{"scripts":{"build":"","test":null,"lint":{"cmd":"eslint"}}}\n',
                encoding="utf-8",
            )

            guesses = sc.detect_verify_commands(root)

            self.assertTrue(guesses["build"].startswith("<FILL:"))
            self.assertTrue(guesses["test"].startswith("<FILL:"))
            self.assertTrue(guesses["lint"].startswith("<FILL:"))

    def test_malformed_package_json_is_safe_and_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text('{"scripts": ', encoding="utf-8")

            guesses = sc.detect_verify_commands(root)

            self.assertTrue(guesses["build"].startswith("<FILL:"))
            self.assertTrue(guesses["test"].startswith("<FILL:"))

    def test_python_tools_are_only_suggested_when_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pyproject = root / "pyproject.toml"
            pyproject.write_text(
                '[project]\nname = "truffle-pytesthelper"\n', encoding="utf-8"
            )
            guesses = sc.detect_verify_commands(root)
            self.assertTrue(guesses["test"].startswith("<FILL:"))
            self.assertTrue(guesses["lint"].startswith("<FILL:"))

            pyproject.write_text(
                '[project.optional-dependencies]\ndev = ["pytest", "ruff"]\n',
                encoding="utf-8",
            )
            guesses = sc.detect_verify_commands(root)
            self.assertEqual(guesses["test"], "python -m pytest")
            self.assertEqual(guesses["lint"], "python -m ruff check .")


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

    def test_force_state_replaces_handoff_symlink_without_touching_target(self) -> None:
        handoff = self.root / "docs" / "SESSION-HANDOFF.md"
        target = self.root / "user-owned-handoff.md"
        target.write_text("DO NOT TOUCH\n", encoding="utf-8")
        handoff.unlink()
        handoff.symlink_to(target)

        r = run_scaffold(["--cwd", str(self.root), "--force-state"])

        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(handoff.is_symlink())
        self.assertIn("STATUS", handoff.read_text(encoding="utf-8"))
        self.assertEqual(target.read_text(encoding="utf-8"), "DO NOT TOUCH\n")
        self.assertIn("state reset", r.stdout)

    def test_force_overwrites_agent_profile(self) -> None:
        agent = self.root / ".grok" / "agents" / "conductor.md"
        agent.write_text("CUSTOM\n", encoding="utf-8")
        r = run_scaffold(["--cwd", str(self.root), "--force"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(agent.read_text(encoding="utf-8"), "CUSTOM\n")
        self.assertIn("conductor", agent.read_text(encoding="utf-8"))
        self.assertIn("template refreshed", r.stdout)

    def test_force_preserves_existing_project_config(self) -> None:
        config = self.root / ".grok" / "config.toml"
        custom = "[mcp.custom]\ncommand = \"user-owned-server\"\n"
        config.write_text(custom, encoding="utf-8")
        r = run_scaffold(["--cwd", str(self.root), "--force"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(config.read_text(encoding="utf-8"), custom)
        self.assertIn("never overwritten", r.stdout)
        self.assertIn("deny rules were NOT merged", r.stdout)

    def test_force_preserves_symlinked_project_config_target(self) -> None:
        config = self.root / ".grok" / "config.toml"
        target = self.root / "user-owned-config.toml"
        custom = "[mcp.custom]\ncommand = \"user-owned-server\"\n"
        target.write_text(custom, encoding="utf-8")
        config.unlink()
        config.symlink_to(target)
        r = run_scaffold(["--cwd", str(self.root), "--force"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(config.is_symlink())
        self.assertEqual(target.read_text(encoding="utf-8"), custom)

    def test_force_replaces_agent_symlink_without_touching_target(self) -> None:
        agent = self.root / ".grok" / "agents" / "conductor.md"
        target = self.root / "user-owned-agent.md"
        target.write_text("DO NOT TOUCH\n", encoding="utf-8")
        agent.unlink()
        agent.symlink_to(target)
        r = run_scaffold(["--cwd", str(self.root), "--force"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(agent.is_symlink())
        self.assertIn("conductor", agent.read_text(encoding="utf-8"))
        self.assertEqual(target.read_text(encoding="utf-8"), "DO NOT TOUCH\n")

    def test_force_replaces_legacy_playbook_symlink_with_copy(self) -> None:
        playbook = self.root / "docs" / "GROK-LONG-RUNNING-PLAYBOOK.md"
        playbook.unlink()
        playbook.symlink_to(REPO_ROOT / "docs" / "PLAYBOOK.md")
        r = run_scaffold(["--cwd", str(self.root), "--force"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(playbook.is_file())
        self.assertFalse(playbook.is_symlink())
        self.assertIn("portable copy refreshed", r.stdout)


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

    def test_grok_47_vocabulary_has_no_retired_commands(self) -> None:
        paths = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "PLAYBOOK.md",
            REPO_ROOT / "docs" / "assets" / "infographic.html",
            REPO_ROOT / "install.sh",
            REPO_ROOT / "long-running-project" / "SKILL.md",
            REPO_ROOT / "long-running-project" / "README.md",
            REPO_ROOT / "long-running-project" / "scripts" / "scaffold.py",
            REPO_ROOT
            / "long-running-project"
            / "references"
            / "templates"
            / "AGENTS.section.md",
            REPO_ROOT
            / "long-running-project"
            / "references"
            / "templates"
            / "grok-config.toml",
            REPO_ROOT
            / "long-running-project"
            / "references"
            / "templates"
            / "project-complete.SKILL.md",
        )
        retired = (
            "/check-work",
            "--experimental-memory",
            "/memory on",
            "--agent-profile",
            "subagent_type",
            "capability_mode",
            "--yolo",
            "--disallowed-tools",
            "grok-4.5",
            "0.2.118",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for token in retired:
                self.assertNotIn(token, text, f"{token} remains in {path}")

        playbook = (REPO_ROOT / "docs" / "PLAYBOOK.md").read_text(encoding="utf-8")
        for token in (
            "grok-4.7",
            "--always-approve",
            "--no-subagents",
            "run_in_background",
            "/project-complete",
        ):
            self.assertIn(token, playbook)

    def test_project_config_uses_only_project_scoped_settings(self) -> None:
        try:
            import tomllib
        except ModuleNotFoundError:
            self.skipTest("tomllib is built into Python 3.11+")

        path = (
            REPO_ROOT
            / "long-running-project"
            / "references"
            / "templates"
            / "grok-config.toml"
        )
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        self.assertIn("permission", data)
        self.assertEqual(len(data["permission"]["rules"]), 4)
        self.assertTrue(
            all(rule["action"] == "deny" for rule in data["permission"]["rules"])
        )
        self.assertNotIn("agent", data)


if __name__ == "__main__":
    unittest.main()
