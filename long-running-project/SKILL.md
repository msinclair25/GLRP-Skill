---
name: long-running-project
description: >
  Activate and scaffold the long-running Grok Build project protocol for the
  current repository. Use when the user says "activate long running project",
  "activate long-running", "set up long running project", "long running mode",
  "enable long-running protocol", or invokes /long-running-project.
  Scaffolds AGENTS.md managed section, docs handoff/feature list, .grok agents,
  a deny-rule template, and project-complete skill. Do not use for one-off questions.
user-invocable: true
argument-hint: "[--force] [--force-state] [--single-agent] [--refresh-agents-section] [optional milestone goal]"
metadata:
  short-description: "Scaffold long-running project protocol"
---

# Activate long-running project

You are activating the **long-running project protocol** for a **project repository**.
This is an **execute** skill, not an essay.

## Goal

1. Confirm the correct project root (never scaffold `$HOME` or a random folder).
2. Scaffold durable on-disk structure (idempotent; protect existing `AGENTS.md`).
3. Explain the folder-trust and new-session step required before project rules are active.
4. Make the existing-config case explicit: GLRP does not silently merge deny rules.
5. Tell the user how to work — including that **memory is optional and not auto-enabled**.
6. If they gave a milestone goal, seed handoff + feature list.

## Steps (do in order)

### 1. Confirm workspace (required — do not skip)

1. Resolve **git toplevel**:
   ```bash
   git rev-parse --show-toplevel
   ```
2. If that fails, **stop** and ask the user to `cd` into their project repo (or pass a path). Do **not** scaffold `$HOME`, `/`, or the system temp root.
3. Show the user the resolved root and existing files briefly:
   - Does `AGENTS.md` already exist?
   - Does `.grok/` already exist?
4. If the session cwd is a **subdirectory** of a monorepo, still use the **git root** unless the user explicitly wants a package subfolder **and** that subfolder is itself a separate git repo.
5. If anything looks wrong (user said project A but cwd is project B), **ask before scaffolding**.

### 2. Run the scaffold script

Always pass the **git root** as `--cwd`:

```bash
python3 "${GROK_HOME:-$HOME/.grok}/skills/long-running-project/scripts/scaffold.py" --cwd "$(git rev-parse --show-toplevel)"
```

**Flags from user arguments:**

| User said | Pass |
|-----------|------|
| `force` / overwrite templates | `--force` (refreshes templates + AGENTS block; does **not** wipe state or an existing `.grok/config.toml`) |
| `force state` / reset handoff | `--force-state` (destructive to SESSION-HANDOFF / FEATURE-LIST / progress) |
| `refresh agents` / update protocol block | `--refresh-agents-section` |
| `single agent` / no multi-agent | `--single-agent` |
| do not touch AGENTS.md | `--no-agents-merge` |
| not a git repo (rare) | `--allow-non-git` only after user confirms |

**AGENTS.md protection (built into script):**

- Never rewrites the whole file.
- If no markers: **appends** the managed block only.
- If managed block already exists: **leaves it alone** unless `--refresh-agents-section` or `--force`.
- Content **outside** `<!-- LONG-RUNNING-PROJECT:START -->` … `END` is never modified by refresh.
- Broken/duplicate/reversed markers fail before any scaffold files are created.
- A symlinked `AGENTS.md` is not followed; use a project-local file or `--no-agents-merge`.
- A planned file whose parent symlink resolves outside the project root is refused before writes begin.

If `python3` fails, try `python`. Only if both fail, create files from templates under:

`${GROK_HOME:-$HOME/.grok}/skills/long-running-project/references/templates/`

following the same safety rules (git root, no clobber of full AGENTS.md).

### 3. Fill verify commands (only if placeholders remain)

Open `AGENTS.md` managed section. If verify lines still contain `<!-- VERIFY_* -->` or `<FILL:…>`:

- Infer from package manifests / README.
- Replace placeholders only — do not rewrite user-edited commands.
- If unknown, leave TODO and mention once in the summary.

### 4. Check project config result

- If `.grok/config.toml` was created, say that the recommended destructive-command denies were installed.
- If it already existed, say plainly that it was preserved and GLRP's deny rules were **not merged**. Show the template path printed by the script and ask the user to review/merge the rules they want.
- Never imply the project has GLRP deny protection merely because activation otherwise succeeded.

### 5. Seed milestone (if user provided a goal)

Only edit handoff/feature list if those files are new or still templates — **do not wipe** user-filled SESSION-HANDOFF without asking.

### 6. Explain trust and reload (required)

The files are now **scaffolded**, but do not claim they are fully active in the current session:

- Grok loads project `AGENTS.md` and project config at session start.
- Project rules, skills, and permission config are ignored until the folder is trusted.
- Tell the user to review the generated diff, then open a **new Grok session** in the project and approve the folder-trust prompt. From the CLI they may launch in the project with `grok --trust` when they intentionally trust it.
- Do not grant trust automatically or imply that trust bypasses the permission rules.

### 7. Memory — recommend on, but do NOT auto-enable

**GLRP does not flip experimental memory** (global user choice).

- Handoff files work **without** memory; protocol is complete either way.
- **Recommend** users enable it for long-running work (better recall + `/flush` / `/remember`).

Tell them clearly:

| Method | How |
|--------|-----|
| Persistent (recommended) | `[memory] enabled = true` in the Grok-home `config.toml` |
| One session | `GROK_MEMORY=1 grok` |
| Mid-session | Open `/memory`, then press `t` to toggle |

Do not silently edit their global `config.toml` unless they ask.

### 8. Report activation card

```markdown
## Long-running project: SCAFFOLDED

**Root:** … (must be the intended git project)
**Scaffold:** created / updated / skipped counts

### AGENTS.md
- Existing body preserved
- Managed section: created | appended | left as-is | refreshed (only if requested)

### Files
- docs/SESSION-HANDOFF.md, FEATURE-LIST.md, progress.txt, …
- .grok/config.toml — created with deny rules | existing file preserved and deny rules **not merged** (show comparison template)
- .grok/agents/* (unless --single-agent)
- docs/GROK-LONG-RUNNING-PLAYBOOK.md (portable copy, not a machine-local symlink)

### Activate in Grok
- Review the generated diff
- Start a new Grok session in this project
- Approve folder trust when prompted (or intentionally launch with `grok --trust`)
- Project AGENTS.md/config load at session start after trust

### Memory
- **Not auto-enabled by GLRP** (by design).
- **Recommended:** enable with `[memory] enabled = true` in the Grok-home `config.toml`, `GROK_MEMORY=1 grok`, or toggle it from `/memory`
- Handoff files still required even when memory is on

### How to work
1. Fill FEATURE-LIST + SESSION-HANDOFF
2. Checklist prompts; project verify commands + `/project-complete` after multi-part code
3. Before /compact or /new: update handoff (+ `/flush` if memory is on)
```

### 9. Completeness for *this* skill

- [ ] Git root confirmed with user-visible path
- [ ] Scaffold ran against that root only
- [ ] AGENTS.md not wholesale replaced
- [ ] Existing `.grok/config.toml` not overwritten
- [ ] Existing-config case states whether GLRP deny rules are actually present
- [ ] Trust + new-session requirement explained
- [ ] Memory called out as optional / not auto-on
- [ ] No unrelated product code changes

## What this skill does *not* do

- Enable memory or change global Grok config
- Trust the project or restart Grok automatically
- Install MCP, always-approve, or sandbox profiles
- Commit to git
- Replace an entire existing `AGENTS.md`
- Scaffold outside a project without explicit unsafe flags

## Re-activate / upgrade

- Default re-run: **skips** existing files; **keeps** existing managed AGENTS section.
- To pull new protocol text into the managed block only: `--refresh-agents-section`.
- To overwrite non-state scaffold templates (docs, agents, project skill): `--force` (ask user first on mature repos). Existing project config and milestone state remain protected.
