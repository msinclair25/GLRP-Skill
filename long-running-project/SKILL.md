---
name: long-running-project
description: >
  Activate and scaffold the long-running Grok Build project protocol for the
  current repository. Use when the user says "activate long running project",
  "activate long-running", "set up long running project", "long running mode",
  "enable long-running protocol", or invokes /long-running-project.
  Scaffolds AGENTS.md managed section, docs handoff/feature list, .grok agents,
  deny rules, and project-complete skill. Do not use for one-off questions.
user-invocable: true
argument-hint: "[--force] [--single-agent] [optional milestone goal]"
metadata:
  short-description: "Scaffold long-running project protocol"
---

# Activate long-running project

You are activating the **long-running project protocol** for the **current workspace**
(the repo / cwd of this Grok session). This is an **execute** skill, not an essay.

## Goal

1. Scaffold durable on-disk structure (idempotent).
2. Wire shared `AGENTS.md` rules + multi-agent profiles (unless single-agent).
3. Tell the user exactly how to work from here.
4. If they gave a milestone goal, seed handoff + feature list and stop ready to work.

## Steps (do in order)

### 1. Confirm workspace

- Resolve project root (git root if available, else cwd).
- Briefly note existing `AGENTS.md`, `docs/`, `.grok/` so the user knows what will change.

### 2. Run the scaffold script

Run this from the project root (adjust path only if skill root differs):

```bash
python3 "$HOME/.grok/skills/long-running-project/scripts/scaffold.py" --cwd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

**Flags from user arguments:**

| User said | Pass |
|-----------|------|
| `force` / overwrite | `--force` |
| `single agent` / no multi-agent | `--single-agent` |
| do not touch AGENTS.md | `--no-agents-merge` |

If `python3` fails, create the same files using templates under:

`$HOME/.grok/skills/long-running-project/references/templates/`

following the script’s layout (do not invent a different structure).

### 3. Fill verify commands

Open `AGENTS.md` managed section. If verify lines still contain `<FILL:…>`:

- Infer from `package.json` / `Cargo.toml` / `pyproject.toml` / `go.mod` / README.
- Replace placeholders with real commands.
- If unknown, leave clear `TODO` and ask the user once in the final summary.

### 4. Seed milestone (if user provided a goal)

If the user stated what they are building:

1. Update `docs/SESSION-HANDOFF.md` with STATUS, goal, acceptance stubs, date.
2. Put 3–10 concrete checkboxes in `docs/FEATURE-LIST.md`.
3. Append one line to `docs/progress.txt`: activation note.

If no goal was given, leave templates and list what they should fill.

### 5. Memory (optional, non-blocking)

If memory tools are available, offer or run:

- `/memory on` is user-toggled — tell them to enable if off.
- Suggest `/remember` once: long-running protocol active; handoff at docs/SESSION-HANDOFF.md.

Do not fail the skill if memory is disabled.

### 6. Report activation card

Print a compact Markdown card:

```markdown
## Long-running project: ACTIVE

**Root:** …
**Scaffold:** created / updated / skipped counts

### Files
- AGENTS.md (managed section)
- docs/SESSION-HANDOFF.md, FEATURE-LIST.md, progress.txt, ROADMAP.md, DECISIONS.md
- .grok/config.toml (deny rules)
- .grok/agents/{conductor,explorer,implementer,reviewer}.md  (unless --single-agent)
- .grok/skills/project-complete/

### How to work from now on
1. Put acceptance in FEATURE-LIST + SESSION-HANDOFF before big work.
2. Use checklist prompts (“Done means ALL of: …”).
3. After multi-part or code: `/check-work` then update handoff.
4. Before /compact or /new: update handoff + `/flush`.
5. Delegate only independent work; prefer .grok/agents/* profiles.
6. Deep reference: docs/GROK-LONG-RUNNING-PLAYBOOK.md (if linked) or
   ~/Documents/CodexSolLunaRoleKit/Grok Build - Long Running Project Playbook.md

### Your next command
@docs/SESSION-HANDOFF.md @docs/FEATURE-LIST.md
Continue milestone: <goal or "fill FEATURE-LIST first">
```

### 7. Completeness for *this* skill

Before ending:

- [ ] Scaffold script ran (or equivalent files written)
- [ ] AGENTS managed section present (unless --no-agents-merge)
- [ ] Verify commands best-effort filled
- [ ] Activation card shown
- [ ] No unrelated refactors

Do **not** implement product features unless the user also asked for that in the same message.

## What this skill does *not* do

- Change global `~/.grok/config.toml` (user must enable memory / effort themselves if desired).
- Install MCP servers or enable always-approve.
- Commit to git (offer commit only if user asks).
- Replace an existing carefully written AGENTS.md body — it only maintains the
  `<!-- LONG-RUNNING-PROJECT:START -->` … `END` section.

## Re-activate / upgrade

Running again refreshes the managed AGENTS section and skips existing files unless `--force`.
Safe to re-run after skill template updates.
