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
argument-hint: "[--force] [--single-agent] [--refresh-agents-section] [optional milestone goal]"
metadata:
  short-description: "Scaffold long-running project protocol"
---

# Activate long-running project

You are activating the **long-running project protocol** for a **project repository**.
This is an **execute** skill, not an essay.

## Goal

1. Confirm the correct project root (never scaffold `$HOME` or a random folder).
2. Scaffold durable on-disk structure (idempotent; protect existing `AGENTS.md`).
3. Tell the user how to work — including that **memory is optional and not auto-enabled**.
4. If they gave a milestone goal, seed handoff + feature list.

## Steps (do in order)

### 1. Confirm workspace (required — do not skip)

1. Resolve **git toplevel**:
   ```bash
   git rev-parse --show-toplevel
   ```
2. If that fails, **stop** and ask the user to `cd` into their project repo (or pass a path). Do **not** scaffold `$HOME`, `/`, or a temp directory.
3. Show the user the resolved root and existing files briefly:
   - Does `AGENTS.md` already exist?
   - Does `.grok/` already exist?
4. If the session cwd is a **subdirectory** of a monorepo, still use the **git root** unless the user explicitly wants a package subfolder **and** that subfolder is itself a separate git repo.
5. If anything looks wrong (user said project A but cwd is project B), **ask before scaffolding**.

### 2. Run the scaffold script

Always pass the **git root** as `--cwd`:

```bash
python3 "$HOME/.grok/skills/long-running-project/scripts/scaffold.py" --cwd "$(git rev-parse --show-toplevel)"
```

**Flags from user arguments:**

| User said | Pass |
|-----------|------|
| `force` / overwrite files | `--force` (also refreshes managed AGENTS section) |
| `refresh agents` / update protocol block | `--refresh-agents-section` |
| `single agent` / no multi-agent | `--single-agent` |
| do not touch AGENTS.md | `--no-agents-merge` |
| not a git repo (rare) | `--allow-non-git` only after user confirms |

**AGENTS.md protection (built into script):**

- Never rewrites the whole file.
- If no markers: **appends** the managed block only.
- If managed block already exists: **leaves it alone** unless `--refresh-agents-section` or `--force`.
- Content **outside** `<!-- LONG-RUNNING-PROJECT:START -->` … `END` is never modified by refresh.

If `python3` fails, try `python`. Only if both fail, create files from templates under:

`$HOME/.grok/skills/long-running-project/references/templates/`

following the same safety rules (git root, no clobber of full AGENTS.md).

### 3. Fill verify commands (only if placeholders remain)

Open `AGENTS.md` managed section. If verify lines still contain `<!-- VERIFY_* -->` or `<FILL:…>`:

- Infer from package manifests / README.
- Replace placeholders only — do not rewrite user-edited commands.
- If unknown, leave TODO and mention once in the summary.

### 4. Seed milestone (if user provided a goal)

Only edit handoff/feature list if those files are new or still templates — **do not wipe** user-filled SESSION-HANDOFF without asking.

### 5. Memory — NOT activated by this skill

**GLRP does not enable experimental memory.** Users must opt in themselves:

| Method | Command / config |
|--------|------------------|
| One session | `grok --experimental-memory` |
| Env | `export GROK_MEMORY=1` |
| Persistent | `[memory] enabled = true` in `~/.grok/config.toml` |
| Mid-session | `/memory on` |

Handoff files work **without** memory. Memory is optional sugar (`/flush`, `/remember`).

Tell the user this clearly in the activation card.

### 6. Report activation card

```markdown
## Long-running project: ACTIVE

**Root:** … (must be the intended git project)
**Scaffold:** created / updated / skipped counts

### AGENTS.md
- Existing body preserved
- Managed section: created | appended | left as-is | refreshed (only if requested)

### Files
- docs/SESSION-HANDOFF.md, FEATURE-LIST.md, progress.txt, …
- .grok/config.toml (deny rules) — only if newly created
- .grok/agents/* (unless --single-agent)

### Memory
- **Not enabled by GLRP.** Optional: `grok --experimental-memory` or `/memory on`

### How to work
1. Fill FEATURE-LIST + SESSION-HANDOFF
2. Checklist prompts; `/check-work` after multi-part code
3. Before /compact or /new: update handoff (+ `/flush` if memory is on)
```

### 7. Completeness for *this* skill

- [ ] Git root confirmed with user-visible path
- [ ] Scaffold ran against that root only
- [ ] AGENTS.md not wholesale replaced
- [ ] Memory called out as optional / not auto-on
- [ ] No unrelated product code changes

## What this skill does *not* do

- Enable `--experimental-memory` or change global Grok config for memory
- Install MCP, always-approve, or sandbox profiles
- Commit to git
- Replace an entire existing `AGENTS.md`
- Scaffold outside a project without explicit unsafe flags

## Re-activate / upgrade

- Default re-run: **skips** existing files; **keeps** existing managed AGENTS section.
- To pull new protocol text into the managed block only: `--refresh-agents-section`.
- To overwrite scaffold templates (docs agents, etc.): `--force` (ask user first on mature repos).
