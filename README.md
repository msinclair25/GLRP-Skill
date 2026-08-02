# GLRP Skill

<p align="center">
  <img src="docs/assets/social-preview.png" alt="GLRP — Long-Running Project Skill. Activate. Scaffold. Ship." width="100%" />
</p>

**Grok Long-Running Project** — a [Grok Build](https://docs.x.ai/build/overview) skill that turns any repo into a durable, multi-session agentic coding workspace.

Say this in a Grok session (from your project directory):

```text
activate long running project
```

or:

```text
/long-running-project
```

GLRP scaffolds the files and conventions that keep coding agents effective over **hours and days**: external handoff state, feature checklists, thin shared `AGENTS.md` rules, multi-agent profiles, safety denies, and a completeness ritual — without pasting a giant playbook into every prompt.

<p align="center">
  <img src="docs/assets/infographic.png" alt="GLRP protocol: activate skill, scaffold repo, work in milestones, verify with check-work" width="720" />
</p>

---

## Why this exists

Long agent sessions fail in predictable ways:

| Failure | GLRP response |
|---------|----------------|
| Context fills / agent “forgets” | `docs/SESSION-HANDOFF.md` + fresh sessions |
| “Done” when work is incomplete | Checklists, `/check-work`, feature list |
| Fat always-on rules hurt quality | Thin managed `AGENTS.md` section only |
| Parallel agents collide | Worktree-aware roles under `.grok/agents/` |
| Tests deleted to go green | **Test ratchet** in shared rules |
| Re-explaining the protocol every repo | One skill install → activate per project |

The full design notes live in [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md).

---

## Requirements

- [Grok Build CLI](https://x.ai/cli) (skill discovery under `~/.grok/skills/`)
- Python 3 (for the scaffold script)
- Git (recommended; used to resolve project root)

---

## Install

**Copy-paste one line** (macOS, Linux, Windows Git Bash / WSL, or Grok Build):

```bash
rm -rf "${TMPDIR:-/tmp}/GLRP-Skill" && git clone --depth 1 https://github.com/msinclair25/GLRP-Skill.git "${TMPDIR:-/tmp}/GLRP-Skill" && bash "${TMPDIR:-/tmp}/GLRP-Skill/install.sh" && rm -rf "${TMPDIR:-/tmp}/GLRP-Skill"
```

That clones the repo, installs into `~/.grok/skills/long-running-project/`, adds a short pointer in `~/.grok/AGENTS.md` if needed, then removes the temp clone.

### Platform support

| Platform | Install one-liner | Notes |
|----------|-------------------|--------|
| **macOS** | Yes | Terminal or Grok Build shell |
| **Linux** | Yes | bash + git + python3 for activate/scaffold |
| **Windows (WSL)** | Yes | Same as Linux inside WSL |
| **Windows (Git Bash)** | Yes | Install [Git for Windows](https://gitforwindows.org/); use Git Bash (or Grok’s bash-friendly shell) |
| **Windows (PowerShell only)** | Not as-is | No bash/`/tmp` semantics — use Git Bash, WSL, or clone then `bash install.sh` |

**Needs:** `git`, `bash`, and for **activate** (scaffold): `python3` (on Windows: `python`/`py` often works if `python3` is on PATH; Grok may invoke `python3` — install Python 3 and ensure `python3` is available).

Open a **new** Grok session (or restart) so skills reload. Optional check:

```bash
grok inspect
```

Look for `long-running-project` in the skills list.

---

## Activate (per project)

In any project session:

```text
activate long running project
```

**Optional arguments:**

| Say / pass | Effect |
|------------|--------|
| `force` | Overwrite scaffold templates (agents, config, roadmap…) + refresh managed AGENTS section — **does not** wipe handoff/feature-list |
| `force state` / `--force-state` | Reset SESSION-HANDOFF / FEATURE-LIST / progress (destructive) |
| `refresh agents` / `--refresh-agents-section` | Update **only** the managed AGENTS block (keep rest of file) |
| `single agent` / `--single-agent` | Skip multi-agent `.grok/agents/*` profiles |
| `no agents merge` / `--no-agents-merge` | Do not touch `AGENTS.md` |
| a milestone goal in the same message | Seeds handoff + feature list |

**Without Grok** (script only):

```bash
cd /path/to/your/repo
python3 ~/.grok/skills/long-running-project/scripts/scaffold.py
# or from this clone:
python3 /path/to/GLRP-Skill/long-running-project/scripts/scaffold.py --cwd .
```

---

## What gets created in your repo

```text
your-repo/
  AGENTS.md                          # managed section (safe merge)
  docs/
    SESSION-HANDOFF.md               # resume packet
    FEATURE-LIST.md                  # external done-conditions
    progress.txt                     # append-only lab notes
    ROADMAP.md
    DECISIONS.md
    GROK-LONG-RUNNING-PLAYBOOK.md    # symlink/pointer when available
  .grok/
    config.toml                      # deny destructive bash/git
    agents/
      conductor.md
      explorer.md
      implementer.md
      reviewer.md
    skills/
      project-complete/SKILL.md      # completeness ritual
```

### `AGENTS.md` merge behavior (safe by default)

GLRP only touches this marked block:

```html
<!-- LONG-RUNNING-PROJECT:START -->
… protocol rules …
<!-- LONG-RUNNING-PROJECT:END -->
```

| Situation | Behavior |
|-----------|----------|
| No `AGENTS.md` | Creates file + managed block |
| `AGENTS.md` exists, no markers | **Appends** managed block; your existing text is unchanged |
| Managed block already present | **Leaves it alone** (your edits kept) |
| `--refresh-agents-section` or `--force` | Replaces **only** the managed block; everything outside markers is preserved |
| `--no-agents-merge` | Does not touch `AGENTS.md` at all |

GLRP **never** deletes or rewrites your whole agents file.

### Project root (cwd) safety

Activate / scaffold:

- Resolves the **git repository root** (not a random nested folder).
- **Refuses** `$HOME`, filesystem root, and temp dirs unless you pass `--allow-unsafe-cwd`.
- **Refuses** non-git folders unless you pass `--allow-non-git`.

Always run activate from the project you intend (or tell Grok the path).

### Verify commands

Best-effort detect `npm` / `cargo` / `pytest` / `go`. Only fills remaining `<!-- VERIFY_* -->` placeholders — does not overwrite commands you already edited.

---

## Memory (recommended — you turn it on yourself)

**Long-running projects work without experimental memory.** GLRP’s handoff files (`SESSION-HANDOFF`, `FEATURE-LIST`, `progress.txt`) are the source of truth on disk, so multi-session work is fine with memory **off**.

**Most people will still want memory on.** It adds cross-session recall, `/flush` summaries, and `/remember` notes so Grok is less blank-slate between sessions. **Install and activate do not flip this for you** (memory is experimental and global — we leave the choice to you).

### Recommended: enable once, keep it on

Add to `~/.grok/config.toml`:

```toml
[memory]
enabled = true
```

Or for a single session:

```bash
grok --experimental-memory
```

| Scope | How |
|-------|-----|
| **Persistent (recommended)** | `[memory] enabled = true` in `~/.grok/config.toml` |
| One session | `grok --experimental-memory` |
| Env | `export GROK_MEMORY=1` |
| Mid-session | `/memory on` |

### How GLRP + memory work together

| Layer | Role |
|-------|------|
| **Handoff files** | Required protocol — milestone state, acceptance, next steps (always use these) |
| **Experimental memory** | Recommended helper — search/recall + `/flush` / `/remember` |

Even with memory **on**, update handoff before `/compact` or `/new`, and run `/flush` at milestone boundaries so useful session detail is saved.

---

## Safety & conflicts

### Install only (one-liner)

| Touches | Risk |
|---------|------|
| `~/.grok/skills/long-running-project/` | Low — skill package only; re-install **replaces** this skill folder |
| `~/.grok/AGENTS.md` | Low — **appends** a short pointer if missing; does not rewrite the whole file |
| Your git repos / code | **None** |
| Global model, MCP, always-approve, sandbox | **None** |

**Conflicts:** another skill already named `long-running-project` gets overwritten on re-install. Uninstall: `rm -rf ~/.grok/skills/long-running-project`.

### Activate (per project)

| Touches | Risk |
|---------|------|
| New `docs/*`, `.grok/*` | Low — **skips** files that already exist (unless `--force`) |
| Existing `AGENTS.md` | **Protected** — append managed block or leave existing block alone (see above) |
| New `.grok/config.toml` | Medium — adds **deny** rules for force-push / hard-reset / broad `rm -rf` (only if file is created) |
| Agent behavior | Medium — more checklists, less casual subagent spam, test ratchet |

**Not done by activate:** commits, pushes, memory enablement, overwriting your full AGENTS.md.

### Recommended practice

1. Install skill once on the machine.  
2. **Turn on memory** in `~/.grok/config.toml` (`[memory] enabled = true`) — recommended.  
3. `cd` into the **correct git project**.  
4. Activate without `--force` on mature repos.  
5. Review the managed `AGENTS.md` block and verify commands.  
6. Commit scaffold files if you want them shared with the team.  
7. Use `--refresh-agents-section` only when upgrading protocol text on purpose.

### Undo project activate

- Delete files you do not want under `docs/` / `.grok/`.  
- Remove the managed block between the `LONG-RUNNING-PROJECT` markers from `AGENTS.md`.  
- Or `git checkout --` those paths if you had not committed yet.

---

## Day-to-day workflow (after activate)

1. **Define done** in `docs/FEATURE-LIST.md` and `docs/SESSION-HANDOFF.md`.  
2. Prompt with a checklist: *“Done means ALL of: …”*  
3. Prefer project agents (`.grok/agents/*`) for research / implement / review.  
4. After multi-part or code work: `/check-work`, then update handoff.  
5. Before `/compact` or `/new`: update handoff; `/flush` if memory is enabled (recommended).  
6. Re-activate anytime to refresh the managed AGENTS section after skill upgrades.

---

## Repository layout

```text
GLRP-Skill/
  README.md                 # this file
  LICENSE
  install.sh                # install into ~/.grok/skills
  docs/
    PLAYBOOK.md             # full long-running playbook
  long-running-project/     # the Grok skill package
    SKILL.md                # agent instructions for “activate…”
    scripts/scaffold.py     # idempotent installer for a repo
    references/templates/   # files copied into projects
    README.md               # skill-local notes
```

---

## Design principles (short)

- **Filesystem is memory** — agents may be amnesiac across sessions; handoff + feature list are not.  
- **Thin shared rules, fat roles elsewhere** — `AGENTS.md` is the constitution; `.grok/agents/` is per-role.  
- **Generator ≠ judge** — implement and review/accept separately.  
- **Test ratchet** — never delete tests to go green.  
- **Earned rules** — grow `AGENTS.md` when agents fail for real reasons, not “just in case.”  

See [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md) for industry patterns (Ralph loop, budgets, worktrees, etc.).

---

## Uninstall

```bash
rm -rf ~/.grok/skills/long-running-project
# optional: remove the managed AGENTS section from each project by hand
```

Project files (`docs/*`, `.grok/*`, managed AGENTS block) remain until you delete them.

---

## Tests

```bash
python3 -m unittest discover -s tests -v
```

CI runs the same suite on Ubuntu and macOS (see `.github/workflows/test.yml`).

## Contributing

PRs welcome: template tweaks, better language detection for verify commands, installers for other agents that honor `AGENTS.md`. Run the test suite before opening a PR.

---

## License

[MIT](LICENSE)

---

## Credits

Built for [Grok Build](https://docs.x.ai/build/overview) / SpaceXAI CLI skill discovery. Inspired by long-running agent harness practice (external handoff state, plan/worker/judge separation, worktrees) and the open [AGENTS.md](https://agents.md/) ecosystem format.
