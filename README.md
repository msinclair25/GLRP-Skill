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

### One-liner (clone + install)

```bash
git clone https://github.com/msinclair25/GLRP-Skill.git
cd GLRP-Skill
chmod +x install.sh
./install.sh
```

This copies `long-running-project/` into:

```text
~/.grok/skills/long-running-project/
```

and adds a short pointer to `~/.grok/AGENTS.md` if needed.

### Manual

```bash
cp -R long-running-project ~/.grok/skills/long-running-project
# optional playbook next to skill for handoff symlink
mkdir -p ~/.grok/skills/long-running-project/docs
cp docs/PLAYBOOK.md ~/.grok/skills/long-running-project/docs/
```

Restart Grok or open a **new** session so skills reload. Confirm:

```bash
grok inspect | grep -i long-running
```

---

## Activate (per project)

```bash
cd /path/to/your/repo
grok
```

Then:

```text
activate long running project
```

**Optional arguments:**

| Say / pass | Effect |
|------------|--------|
| `force` | Overwrite existing scaffold files |
| `single agent` / `--single-agent` | Skip multi-agent `.grok/agents/*` profiles |
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

### `AGENTS.md` merge behavior

GLRP maintains only this marked block:

```html
<!-- LONG-RUNNING-PROJECT:START -->
… protocol rules …
<!-- LONG-RUNNING-PROJECT:END -->
```

- Creates `AGENTS.md` if missing  
- Appends the block if your file has no markers  
- **Refreshes** the block on re-activate (your content outside the markers is kept)  

### Verify commands

The scaffold best-effort detects `npm` / `cargo` / `pytest` / `go` commands and fills placeholders. Edit remaining `TODO` / `<FILL:…>` lines in `AGENTS.md`.

---

## Day-to-day workflow (after activate)

1. **Define done** in `docs/FEATURE-LIST.md` and `docs/SESSION-HANDOFF.md`.  
2. Prompt with a checklist: *“Done means ALL of: …”*  
3. Prefer project agents (`.grok/agents/*`) for research / implement / review.  
4. After multi-part or code work: `/check-work`, then update handoff.  
5. Before `/compact` or `/new`: update handoff + `/flush` (if memory is on).  
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

## Contributing

PRs welcome: template tweaks, better language detection for verify commands, installers for other agents that honor `AGENTS.md`.

---

## License

[MIT](LICENSE)

---

## Credits

Built for [Grok Build](https://docs.x.ai/build/overview) / SpaceXAI CLI skill discovery. Inspired by long-running agent harness practice (external handoff state, plan/worker/judge separation, worktrees) and the open [AGENTS.md](https://agents.md/) ecosystem format.
