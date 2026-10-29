---
title: Grok Build — Long-Running Project Playbook
aliases:
  - Grok Build Playbook
  - Long Running Grok Build Instructions
type: playbook
status: active
cli_version_verified: "1.0.41"
model_default: grok-4.7
created: 2026-08-01
updated: 2026-10-15
owner: ms
tags:
  - grok-build
  - playbook
  - long-running
  - agent-ops
  - multi-agent
---

# Grok Build — Full Feature Map + Long-Running Project Playbook

> [!important] How to use this file
> 1. **Read once** for how Grok Build works (Parts I–II).  
> 2. **Copy Part III templates** into every project (thin shared `AGENTS.md`, `.grok/agents/`, skills, memory, hooks).  
> 3. **Follow Part IV session protocol** on every long-running effort.  
> 4. **Use Part V anti-laziness rules** so multi-part asks finish in one pass.  
> Verified against Grok Build CLI **1.0.41**, its installed help/user guide, `grok inspect`, the live Grok Build model catalog, and current xAI Build documentation. Re-check `/docs`, `grok models`, and `/context` after upgrades because Build capabilities can change independently of the public API.
>
> **2026-10-13:** Grok 4.7 migration — current agent/memory/headless commands, folder-trust lifecycle, portable scaffold, and `/project-complete` verification flow.
>
> **2026-10-15:** Review hardening — preflight-safe AGENTS merging, symlink-safe state resets, conservative package-aware verify detection, staged rollback-safe skill install, and explicit existing-config guidance.

---

# Part I — What Grok Build is

## 1. Product shape

**Grok Build** (CLI / TUI from xAI) is an interactive coding agent that:

- Reads and edits your repo
- Runs shell commands
- Searches code and the web
- Spawns subagents with separate context
- Persists sessions to disk
- Extends via skills, MCP, hooks, plugins, workflows

**Three ways to run it:**

| Mode | Command | Use for |
|------|---------|---------|
| Interactive TUI | `grok` | Day-to-day coding, long projects |
| Headless | `grok -p "…"` | CI, scripts, one-shot automation |
| Agent / ACP | `grok agent stdio` / `serve` | IDEs, custom clients |

Auth: browser login (default) or `XAI_API_KEY`. Config: `~/.grok/config.toml`. State: `~/.grok/` (sessions, memory, skills, auth).

---

## 2. Mental model (how a turn works)

```
You type prompt
    → system prompt + AGENTS.md + skills listing + memory (if on)
    → model reasons
    → tool calls (read/edit/bash/search/web/subagent/…)
    → tool results return
    → model continues until it decides the turn is "done"
    → Stop event (hooks can block stop)
    → session saved under ~/.grok/sessions/<encoded-cwd>/<session-id>/
```

**Critical gap for long projects:** the model still decides when its turn is done; there is no universal multi-part acceptance gate. Current Grok Build no longer bundles the earlier dedicated completeness command. Use explicit acceptance checklists, the project `/project-complete` skill, real build/test/lint commands, and—when risk warrants it—`/review`, an independent reviewer, or `/goal`'s verification loop.

---

## 3. Context window and compaction

| Concept | Default / notes |
|---------|-----------------|
| Grok 4.7 public API context | 500k tokens |
| Grok Build session context | Read the live `grok models` / `/context` value; the cached Build 4.7 entry used for this review reported 256k, so do not assume the API limit |
| Auto-compact | Catalog/config dependent (`[session] auto_compact_threshold_percent`); the 1.0.41 guide says 85% while some model metadata advertises 80% |
| Manual compact | `/compact` or `/compact keep X Y Z` |
| Memory around compact | Current memory can auto-flush before compaction; use `/flush` for an explicit checkpoint and keep the handoff file authoritative |
| Plan mode + compact | Plan state is preserved across compact |

**Long-run rule:** treat context as **working memory**, not archive. Milestone → flush → compact or `/new` with handoff note.

Current Grok Build enables two-pass compaction by default. Treat that as an implementation default, not a reason to skip the handoff: the durable record still belongs in project files and memory before compaction.

Check usage anytime: `/context`, `/session-info` (aliases `/status`, `/info`). Credits: `/usage`.

---

# Part II — Feature and tool map

## 4. Built-in tools (agent capabilities)

These are the primary tools the model calls (names may appear slightly differently in UI vs API):

### File & code

| Tool | Purpose |
|------|---------|
| `read_file` | Read files (also PDF/images with limits) |
| `search_replace` | Create/edit files with exact-string replace |
| `list_dir` | Directory listing (respects gitignore by default in listings) |
| `grep` | ripgrep across workspace |
| `run_terminal_command` | Shell with background execution and long-timeout support |

### Task & planning

| Tool | Purpose |
|------|---------|
| `todo_write` | Structured TODO list (visible in TUI) |
| `enter_plan_mode` / `exit_plan_mode` | Structured plan-only phase → approve before code |
| `ask_user_question` | Multiple-choice clarification |
| `workflow` | Launch Rhai multi-agent workflows |
| Goal tooling / `/goal` | Multi-round autonomous goal with verification (when enabled) |

### Parallelism & async

| Tool | Purpose |
|------|---------|
| `spawn_subagent` | Child session; own context; optional worktree isolation |
| `get_command_or_subagent_output` | Poll background cmd / subagent |
| `kill_command_or_subagent` | Stop background work |
| `monitor` | Stream line events from long-running scripts |
| `scheduler_create` / `list` / `delete` | Recurring prompts (`/loop` is the UX) |

### Knowledge & research

| Tool | Purpose |
|------|---------|
| `web_search` / `web_fetch` / `open_page` / etc. | Web research |
| `memory_search` / `memory_get` | Cross-session memory (if memory enabled) |
| MCP: `search_tool` / `use_tool` | External integrations |

### Media (when relevant)

| Tool | Purpose |
|------|---------|
| `image_gen` / `image_edit` / video tools | Media generation |

### Safety note

Hooks (`PreToolUse`) and permission **deny** rules can block tools. Sandbox profiles (OS kernel) can restrict FS/network. Plan mode blocks **file edits** outside the plan file (shell redirections are *not* fully gated).

---

## 5. Subagents

Enabled by default (`[subagents] enabled = true`).

| Built-in type | Can edit files? | Use for |
|---------------|-----------------|---------|
| `general-purpose` | Yes | Implementation, broad work |
| `explore` | No | Codebase research, maps |
| `plan` | No | Implementation plans only |

**Current spawn parameters that matter for long projects:**

- `prompt` + `description` — bounded assignment and short task label
- `isolation: "worktree"` — isolated git worktree (safe parallel writers)
- `run_in_background: true` — non-blocking; poll later
- `resume_from` — continue a finished child's transcript
- `cwd` — different working directory (not with worktree)

Do not pass retired capability, background, or named-type fields to the spawn tool. Put read/write constraints and the required evidence in the assignment, use a read-oriented project agent where available, and inspect the tool schema exposed by the installed release.

**Personas** (`/personas`, `.grok/personas/*.toml`): behavioral overlays for subagents (tone, I/O contracts), not full agent replacements.

**Roles** (`.grok/roles/*.toml` or `[subagents.roles.*]`): reusable capability/model defaults for spawn types (e.g. default `read-only`, model pin, prompt file).

**Custom agent profiles** (`.grok/agents/*.md`, `~/.grok/agents/`, `/config-agents`): full agent definitions—name, tools, `permission_mode`, body prompt, optional `agents_md: true` to load project `AGENTS.md`. Select the primary agent with `grok --agent conductor`, `GROK_AGENT=conductor`, or a **user-level** `[agent]` setting. Project `.grok/config.toml` does not accept `[agent]`.

**Dashboard:** `/dashboard` or `Ctrl+\` opens the session roster. Current CLI/help and docs differ on whether child sessions get their own rows, so treat `Ctrl+G`'s tasks pane as the authoritative subagent view.

**Depth limit (critical):** Only the **top-level** session may spawn subagents. A subagent **cannot** spawn children (max nesting depth = 1). Design trees as **conductor → N workers**, never worker → sub-worker. If a child needs more help, it must return findings to the parent.

**Name shadowing:** A custom agent in `.grok/agents/foo.md` can override a built-in with the same `name`. Prefer distinct names (`explorer` vs built-in `explore`, `implementer` vs `general-purpose`) so you do not silently replace platform defaults.

**Long-run rule:** parallelize **independent** work only; prefer `explore` / project `explorer` for research; one writer per owned paths; use worktrees when two agents edit code.

> [!tip] Multi-agent in one repo
> Do **not** encode every role inside one giant `AGENTS.md`. Use thin shared `AGENTS.md` + one file per role under `.grok/agents/`. Full decision table: **§7.1**.

---

## 6. Sessions

| Action | How |
|--------|-----|
| New | `/new` or `Ctrl+N` |
| Resume | `/resume`, `grok --resume <id>`, `grok -c` (most recent) |
| Fork | `/fork` (optional worktree) |
| Compact | `/compact [keep notes]` |
| Rewind files+history | `/rewind` / `/undo` / Esc Esc (idle) |
| Rename | `/rename` |
| Export | `/export`, `/copy` |
| Info | `/session-info` |
| Delete | `/delete` or dashboard Ctrl+X twice |

**On-disk layout:**

```
~/.grok/sessions/<encoded-cwd>/<session-id>/
  summary.json
  updates.jsonl          # source of truth
  chat_history.jsonl
  plan.md                # plan mode
  signals.json
  compaction_checkpoints/
  …
```

CLI: `grok sessions list`, `grok sessions search "keyword"`.

---

## 7. Project rules (AGENTS.md)

Loaded automatically from repo root → CWD (and home rules). Also: `CLAUDE.md`, `.grok/rules/*.md`, Claude/Cursor compat paths.

| Path | Purpose |
|------|---------|
| `AGENTS.md` | **Shared** project instructions (constitution for all agents) |
| `.grok/rules/*.md` | Extra shared rule files |
| `.grok/skills/` | Project skills (on-demand procedures) |
| `.grok/agents/` | **Per-role** agent profiles (not a substitute for AGENTS.md) |
| `.grok/hooks/` | Project hooks (need folder trust) |
| `.grok/config.toml` | Project MCP, plugins, permission rules (subset) |
| `.grok/workflows/*.rhai` | Project workflows |
| `.grok/personas/*.toml` | Subagent behavioral overlays |
| `.grok/roles/*.toml` | Spawn role defaults (capability/model) |

Deeper `AGENTS.md` wins on conflict **by directory** (e.g. monorepo package), not by agent role. Keep shared rules **short and actionable** (full-file load → context cost for every session).

Inspect: `grok inspect`.

### 7.1 Multi-agent projects: is AGENTS.md enough?

**No — not by itself.** With multiple agents in the **same** folder/project:

| Layer | Path | Who sees it | Put here |
|-------|------|-------------|---------|
| **Project rules** | `AGENTS.md` (root + optional package subdirs) | Every session/agent that loads project instructions | Stack, verify commands, completeness, security, handoff, default-deny delegation |
| **Agent profiles** | `.grok/agents/*.md` | That agent / when spawned as that type | Role identity, tools, model, permission posture, output contract |
| **Personas / roles** | `.grok/personas/`, `.grok/roles/`, config | Subagents | Tone, I/O contracts, capability defaults |
| **Skills** | `.grok/skills/` | On demand | Repeatable procedures (`/project-complete`, review, deploy) |

**Why not one fat AGENTS.md for all roles**

1. **Everyone gets the whole file** — scout/tester still pay for implementer-only prose; noise and conflicts.
2. **No tool/model isolation** — `AGENTS.md` does not select tools; agent definitions do.
3. **Conditionals drift** — “if you are Sol… if you are Luna…” is ignored under pressure.
4. **Wrong axis for monorepos** — nested `AGENTS.md` is for **directories** (frontend vs backend), not **roles** (reviewer vs worker).

**Recommended layout (same project)**

```text
repo/
  AGENTS.md                         # SHARED only — thin constitution
  packages/api/AGENTS.md            # optional package conventions only
  packages/web/AGENTS.md
  .grok/
    agents/
      conductor.md                  # root / integrator
      explorer.md                   # research (read-oriented)
      implementer.md                # write code
      reviewer.md                   # critique
    personas/                       # optional tone overlays
    roles/                          # optional spawn defaults
    skills/
      project-complete/
```

**Decision rule**

| Need | Best home |
|------|-----------|
| All agents run the same tests / never commit secrets | **`AGENTS.md`** |
| One agent is read-only researcher, another implements | **`.grok/agents/<role>.md`** |
| Same type, different tone or I/O contract | **Persona / role** |
| Multi-step procedure anyone can invoke | **Skill** |
| Frontend vs backend conventions | **Nested `AGENTS.md` per package** |

**Agent profile pattern** (mirror bundled `explore`: keep `agents_md: true` so shared project rules still apply):

```markdown
---
name: implementer
description: >
  Bounded implementation worker for this repo. Use when the parent delegates
  a single owned file set with clear acceptance checks.
prompt_mode: full
agents_md: true
---

You own only the bounded implementation delegated by the parent.
Do not spawn further subagents. Edit only assigned paths.
Return a compact evidence packet: what changed, commands run, risks, next action.
```

Switch / inspect: `/config-agents` (alias `/agents`), `GROK_AGENT=conductor grok`, or `grok --agent conductor`. When delegating, describe the bounded outcome and constraints using the spawn schema exposed by the current release; do not assume a named-agent field is available.

**Long-run rule:** thin shared `AGENTS.md` + one definition file per role. Same idea as Sol/Luna role manifests: **shared policy in one place, role manifests separate**.

---

## 8. Skills

Reusable procedure packages (`SKILL.md`). Locations: project / user / bundled / plugins / Claude / Cursor compat.

| Invocation | How |
|------------|-----|
| Explicit | `/skill-name args` or Skills UI |
| Automatic | Model matches `description` / `when-to-use` |
| Force manual only | `disable-model-invocation: true` |

**Essential bundled / user skills for long projects:**

| Skill | When |
|-------|------|
| Project `project-complete` | Checklist/evidence ritual shipped by GLRP; invoke after multi-part work |
| `goal` | Autonomous multi-round work with an independent verification panel |
| `design` | Design docs + review loop |
| `execute-plan` | PR plan DAG implementation |
| `review` | Code review of changes / PR |
| `implement` | Implementation workflows |
| `create-workflow` | Multi-agent Rhai pipelines |
| `pr-babysit` | CI / PR stack babysitting |
| `help` | Grok config help |

Create: `/create-skill`. List: `grok inspect`, `/skills`.

---

## 9. Memory (cross-session)

**Off by default.** Enable:

```toml
# ~/.grok/config.toml
[memory]
enabled = true
```

or launch one session with `GROK_MEMORY=1 grok`. Mid-session, open `/memory` and press `t` to toggle.

| Command | Effect |
|---------|--------|
| `/remember …` | Durable note (confirm UI) |
| `/flush` | LLM summary of session → searchable |
| `/dream` | Consolidate session logs into topics |
| `/memory` | Browse / toggle |

Storage: `~/.grok/memory/MEMORY.md` (global) + workspace hash dir (shared across worktrees of same `origin`).

**Long-run rule:** `/flush` at every milestone **and** before `/compact` or `/new`.

---

## 10. Plan mode

| Enter | `/plan`, Shift+Tab cycle, or agent `enter_plan_mode` |
| Exit | Approve plan via `exit_plan_mode` UI (`a` approve, `s` changes, `q` quit) |
| Constraint | Only `plan.md` is editable; other file edits rejected |
| View later | `/view-plan` |

Use for **ambiguous architecture**, not for typo fixes.

**Caveat:** subagents are **not** bound by parent plan-mode edit gate — a write-capable subagent can still edit while parent plans. Prefer `explore`/`plan` types during planning.

---

## 11. Goals, workflows, loops

| Feature | Purpose |
|---------|---------|
| `/goal <objective>` | Multi-round autonomous work; independent evidence review before complete |
| `/workflow name {args}` | Saved Rhai multi-agent orchestration |
| `/workflows` | Live run dashboard |
| `/deep-research …` | Background research with claim verification |
| `/loop 30m …` | Recurring prompt (min 60s; expires 7d; max 50) |
| `monitor` | Real-time line stream (use `grep --line-buffered`) |

Workflow agent budget: default 128 logical child agents (1–1024).

---

## 12. Permissions, sandbox, hooks

### Permission modes

| Mode | Behavior |
|------|----------|
| ask (default) | Prompt on risky tools |
| auto | Classifier reduces prompts |
| always-approve | Skip prompts; **deny rules still apply** |
| acceptEdits | Edits free; other tools may still ask |

Toggle: `Ctrl+O`, `/always-approve`, `Shift+Tab`, `--always-approve`.

### Deny/allow rules

```toml
[permission]
rules = [
  { action = "deny", tool = "bash", pattern = "rm -rf *" },
  { action = "deny", tool = "bash", pattern = "git push --force*" },
]
```

### Sandbox (OS-level, off by default)

`grok --sandbox workspace` | `read-only` | `strict`

### Hooks (lifecycle automation)

| Event | Useful for long projects |
|-------|---------------------------|
| `SessionStart` | Env setup, print branch/status |
| `PreToolUse` | Block dangerous commands |
| `PostToolUse` | Auto-format after edits |
| `Stop` | **Block “done” unless tests pass / checklist file exists** |
| `PreCompact` / `PostCompact` | Force `/flush` reminder or auto-summary |
| `SubagentStart` / `SubagentStop` | Log / gate children |

Project hooks require **folder trust** (`/hooks-trust` or `--trust`).

---

## 13. MCP, plugins, LSP

- **MCP:** `~/.grok/config.toml` `[mcp_servers.*]` or project `.grok/config.toml`; manage `/mcps`
- **Plugins:** marketplace `/plugins`, `/marketplace`
- **LSP:** `[features] lsp_tools = true` + `.grok/lsp.json` when you want IDE-like diagnostics for the agent

---

## 14. Models and effort

| Control | How |
|---------|-----|
| Default model | `[models] default` or `/model` |
| Effort | `/effort xhigh` \| `high` \| `medium` \| `low` (model-dependent) |
| Per-session | `grok -m grok-4.7 --effort high` |

For long projects: prefer **high effort** on architecture/integration sessions; medium for mechanical multi-file edits after a solid plan.

---

## 15. Headless / CI highlights

```bash
grok -p "…" --always-approve --output-format json
grok -p "…" -r <session-id>           # continue same session
grok -p "…" --max-turns 40            # cap loops
grok -p "…" --no-subagents             # disable child agents
```

Capture `sessionId` from JSON for multi-step pipelines.

---

## 16. Keyboard / UX essentials

| Key / command | Action |
|---------------|--------|
| `Ctrl+O` | Always-approve toggle |
| `Shift+Tab` | Cycle Normal / Plan / Auto (when available) / Always-approve |
| `Ctrl+B` | Background running command |
| `Ctrl+G` | Tasks pane (bg work / subagents) |
| `Ctrl+\` | Agent dashboard |
| `Esc` | Cancel turn (rules vary by mode) |
| `@file` | Attach file/dir to prompt |
| `/btw` | Side question without derailing turn |
| `/usage` | Credits |

---

# Part III — Project setup for long-running work

Do this **once per repository** (and reuse across Grok sessions).

## 17. Directory scaffold

```text
repo/
  AGENTS.md                          # REQUIRED — SHARED rules only (thin; lines earned by failures)
  docs/
    ROADMAP.md                       # milestones, status
    DECISIONS.md                     # ADR-style log
    SESSION-HANDOFF.md               # latest handoff packet
    FEATURE-LIST.md                  # optional: checkbox done-conditions (Anthropic-style)
    progress.txt                     # optional: append-only lab notes (Ralph-style)
  .grok/
    config.toml                      # project deny rules, MCP
    agents/                          # multi-agent: one profile per role
      conductor.md
      explorer.md
      implementer.md
      reviewer.md
    personas/                        # optional subagent tone overlays
    roles/                           # optional spawn capability defaults
    skills/
      project-complete/SKILL.md      # completeness ritual
    hooks/
      stop-require-checklist.json    # optional Stop gate
    workflows/                       # optional multi-agent pipelines
    rules/                           # optional extra shared rules
  .gitignore                         # ignore .env, local secrets
```

Single-agent projects can omit `.grok/agents/` and use only `AGENTS.md`. Multi-agent projects **should** add `.grok/agents/` rather than bloating `AGENTS.md` (see §7.1).

## 18. Recommended `~/.grok/config.toml` (user-global)

```toml
[models]
default = "grok-4.7"

[session]
auto_compact_threshold_percent = 70   # compact earlier on long projects
# optional worktree prompts:
# new_session_worktree_mode = "never"  # ask | always | never
# fork_worktree_mode = "ask"

[memory]
enabled = true

[ui]
permission_mode = "ask"               # use always-approve only when trusted
show_thinking_blocks = true

[features]
codebase_indexing = true
telemetry = false
# two_pass_compaction is enabled by default in current Grok Build

[subagents]
enabled = true

# Optional: pin lighter models for research children
# [subagents.models]
# explore = "grok-4.7-build-fast"     # verify availability with `grok models`
```

Tune permission mode per trust level. For solo trusted laptops, many people use always-approve **plus** deny rules (prefer **project** deny — §18a).

## 18a. Project `.grok/config.toml` (repo-scoped safety)

Project config can carry MCP, plugins, and **permission rules** (not every global key). Commit this so the whole team shares hard limits:

```toml
# .grok/config.toml
[permission]
rules = [
  { action = "deny", tool = "bash", pattern = "rm -rf *" },
  { action = "deny", tool = "bash", pattern = "git push --force*" },
  { action = "deny", tool = "bash", pattern = "git push -f*" },
  { action = "deny", tool = "bash", pattern = "git reset --hard*" },
]
```

Project config is intentionally limited to MCP, plugins, and permission rules. Select `conductor` with `grok --agent conductor`, `GROK_AGENT=conductor grok`, or user-level config—not in this project file.

Folder trust is required before project `AGENTS.md`, skills, config rules, hooks, MCP, and LSP are loaded. Approve the interactive trust prompt or intentionally launch from that folder with `grok --trust`, then start a new session after changing startup-loaded rules. Global `~/.grok` hooks are always trusted.

## 18b. Worktrees (parallel isolation)

| Action | How |
|--------|-----|
| Launch in new worktree | `grok --worktree=feat-name "…"` (use `=` so the prompt is not swallowed) |
| Worktree from branch | `grok -w --ref main "…"` |
| Resume in fresh worktree | `grok -w -r <session-id>` |
| Fork with worktree | `/fork --worktree` |
| Subagent isolation | `isolation: "worktree"` on spawn |
| Merge back | Grok worktree apply flow / normal git merge from worktree path |

Use worktrees when two agents must **edit** without stomping; do not pay worktree cost for pure read-only explore.

## 19. Project `AGENTS.md` template (copy and edit)

Keep this **shared and thin**. Role-specific identity belongs in `.grok/agents/` (§19a), not here.

```markdown
# Project agent rules — long-running work (SHARED)

## Completeness (non-negotiable)
- Multi-part user requests are incomplete until EVERY part is done at full depth.
- Before ending a turn, re-read the latest user message and list unmet requirements.
- If completeness conflicts with brevity, completeness wins.
- After any multi-part or code task, run project verification, then invoke /project-complete.

## Session hygiene
- Prefer milestone-sized work, not infinite threads.
- Maintain docs/SESSION-HANDOFF.md: goal, done, open risks, next 3 steps, key paths, commands.
- Before /compact or /new: /flush memory and update SESSION-HANDOFF.md.
- One coherent milestone per session when practical; start fresh after acceptance.

## Delegation
- Default-deny subagents: spawn only for independent, bounded, provable work.
- Prefer project agent types under .grok/agents/ (or explore/plan) over ad-hoc general-purpose.
- Max one writer set of paths at a time; use worktree isolation for parallel writers.
- Return compact evidence (commands, paths, results) — not raw logs.
- Role details live in .grok/agents/ — do not restate per-role prompts here.

## Quality
- Do not claim done without running the project's verify command (see below).
- Never silently skip tests to save time.
- **Test ratchet:** it is unacceptable to delete, skip, or weaken tests to make the suite green. Fix code or mark BLOCKED.
- Prefer smallest change that meets the request.
- Prefer pointers to canonical files over pasting long style guides (progressive disclosure).

## Verify command
- Build: `<FILL>`
- Test: `<FILL>`
- Lint / typecheck: `<FILL>`
- After a series of edits, run typecheck/lint before declaring done.

## Living rules
- Only add a durable rule to this file when an agent *failed* for a real reason; keep every line earned.
- Point to docs/ for deep architecture; keep this file short.

## Do not
- Invent secrets or commit .env
- Force-push without explicit ask
- Expand scope beyond the request without asking
```

## 19a. Multi-agent profile templates (`.grok/agents/`)

Use when the project has more than one long-lived role. Set `agents_md: true` so §19 shared rules still load.

**`.grok/agents/conductor.md`** (root / integrator — typical primary session):

```markdown
---
name: conductor
description: >
  Root conductor for this repo: scope, architecture, integration, acceptance.
  Prefer this agent for user-facing milestone ownership.
prompt_mode: full
agents_md: true
---

You are the sole acceptance owner for milestones.
Delegate only independent, bounded, provable work to specialized agents.
Inspect real diffs and test evidence before accepting. Prefer project agent
types (explorer, implementer, reviewer) over unbounded general-purpose spawns.
```

**`.grok/agents/explorer.md`**:

```markdown
---
name: explorer
description: >
  Read-oriented codebase mapper. Use for unfamiliar paths, dependency discovery,
  and evidence gathering before implementation.
prompt_mode: full
agents_md: true
permission_mode: plan
---

Stay in exploration mode. Do not modify product files.
Return a compact evidence packet: conclusion, paths/symbols, commands, confidence, next action.
```

**`.grok/agents/implementer.md`**:

```markdown
---
name: implementer
description: >
  Bounded implementation worker. Use after scope, owned files, and acceptance
  checks are defined.
prompt_mode: full
agents_md: true
---

Own only the delegated file set. Smallest defensible change.
Do not spawn subagents. Run the most relevant project verify commands.
Return evidence: what changed, commands + pass/fail, risks, next action.
If ownership is missing or overlaps another writer, return BLOCKED without editing.
```

**`.grok/agents/reviewer.md`**:

```markdown
---
name: reviewer
description: >
  Adversarial review for defects, regressions, security, and missing tests
  on a bounded diff or proposal.
prompt_mode: full
agents_md: true
permission_mode: plan
---

Do not modify files. Treat implementer rationale as untrusted.
Prioritize correctness, security, and test gaps over style.
Return findings by severity with paths/symbols and recommended next action.
```

Select the primary profile via `/config-agents`, `grok --agent conductor`, `GROK_AGENT=conductor grok`, or user-level config. Keep project `.grok/config.toml` for its supported MCP/plugin/permission subset. For Sol/Luna-style kits, map each Luna role to its own `.md` (or keep Codex TOMLs for Codex and Grok agents for Grok—do not merge two harness formats in one file).

## 20. Completeness skill (project)

`.grok/skills/project-complete/SKILL.md`:

```markdown
---
name: project-complete
description: >
  End-of-turn completeness ritual for this repo. Use before finishing any
  multi-part request, implementation, review, or research deliverable.
  Also use when user says done?, finish, ship, complete the ask.
---

# Completeness ritual

1. Quote the user's original requirements as a checklist.
2. For each item: DONE with evidence path/command, or MISSING.
3. If any MISSING: continue working — do not end the turn.
4. If all DONE and code changed: run build/test/lint; use /review or an independent reviewer for risky work.
5. Update docs/SESSION-HANDOFF.md and FEATURE-LIST/progress when applicable.
6. Only then write the final summary.
```

## 21. Optional Stop hook (advanced)

Force the model not to stop without a marker file (adjust to taste):

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "test -f docs/SESSION-HANDOFF.md && grep -q 'STATUS: complete' docs/SESSION-HANDOFF.md || (echo 'Update docs/SESSION-HANDOFF.md with STATUS: complete after finishing the ask' >&2; exit 2)"
          }
        ]
      }
    ]
  }
}
```

> [!warning] Stop-hook pitfall
> Gating on `STATUS: complete` will **block every intermediate turn** of a multi-turn milestone and can thrash the agent. Prefer:
>
> - AGENTS.md completeness rules + explicit project verification and `/project-complete`, or
> - A Stop hook that only enforces **verify commands** (tests green) on code-changing sessions, or  
> - A Stop hook that runs only when a sentinel file exists (e.g. `.grok/request-final-check`).
>
> Do not enable the example above on busy long-running milestones until you have tuned it.

## 22. Memory bootstrap

With memory enabled:

```
/remember This repo uses <stack>. Verify with: <commands>.
/remember Long-running protocol: milestone sessions, flush before compact, verify + project-complete after multi-part.
```

---

# Part IV — Operating protocol for long-running projects

## 23. Milestone lifecycle (standard unit of work)

```
1. DEFINE     Write milestone goal + acceptance checks in SESSION-HANDOFF / chat
2. PLAN       /plan if architecture is ambiguous; else short approach note
3. APPROVE    You accept plan (or skip if trivial)
4. IMPLEMENT  Main agent + optional explore/worker subagents
5. VERIFY     Build/test/lint + /project-complete (+ independent review when warranted)
6. RECORD     Update ROADMAP, DECISIONS, SESSION-HANDOFF; /flush; /remember if durable
7. CUT        /new or /compact with handoff — never carry infinite history
```

## 24. Prompt pattern (every non-trivial request)

Paste this shape (or put it in AGENTS.md and reference it):

```text
Done means ALL of:
1) …
2) …
3) …

Constraints:
- …

After work:
- Run <verify>
- /project-complete
- Update docs/SESSION-HANDOFF.md

Do not stop with only a subset complete. If blocked, say BLOCKED with reason.
```

**Attach context explicitly** when resuming:

```text
@docs/SESSION-HANDOFF.md @docs/ROADMAP.md
Continue milestone from handoff. Do not re-explore finished items.
```

**Use `todo_write`** for multi-part work so the TUI shows remaining items; agent should not clear todos until evidence exists.

## 25. Context budget policy

| Context % | Action |
|-----------|--------|
| < 40% | Continue |
| 40–60% | Finish current sub-milestone; avoid new rabbit holes |
| 60–70% | `/flush`; prepare handoff; consider `/compact keep …` |
| ≥ auto-compact | Ensure handoff file is current **before** auto-compact fires |

Earlier auto-compact (70%) is safer for multi-day work than waiting for 85%.

## 26. Parallel work patterns

| Pattern | How |
|---------|-----|
| Research ∥ implement | Parent plans; `explore` / project `explorer` maps; `implementer` on owned paths |
| Multi-file independent | Subagents + `isolation: worktree`; parent merges |
| Multi-session | Dashboard dispatch; pin active agents; one owner of main branch |
| CI / PR watch | `monitor`, `/loop 5m`, or `/pr-babysit` skill when shipping PRs |
| Design → build | `/design` or plan mode → `execute-plan` / implementer only after approval |

**Topology constraint:** conductor may spawn many children; **children cannot spawn** (depth 1). Fan-out only from the root.

**Never:** two unrestricted writers on the same files without ownership.

**Cost note:** every subagent is a full model session (own tools + tokens). Prefer Sol/conductor-direct for small work; spawn only when independence + size beat overhead. Watch `/usage` on multi-day multi-agent efforts.

## 27. Handoff packet (minimum fields)

Keep `docs/SESSION-HANDOFF.md` always valid:

```markdown
# Session handoff
STATUS: in-progress | complete | blocked
Updated: <ISO date>
Milestone: <name>
Goal: <one paragraph>
Acceptance:
- [ ] …
Done:
- …
Open risks:
- …
Next 3 steps:
1. …
Key paths:
- …
Verify:
- `<command>` → expected
Branch / commit:
- …
```

## 28. Git hygiene with Grok

- Commit at milestone boundaries (you or agent with explicit ask)
- Prefer agent to **not** push unless asked
- Use `/rewind` only with care — it restores files from session snapshots (git is still source of truth for committed work)
- Worktrees for experimental agent lanes; apply/merge deliberately (§18b)
- Keep `.env`, secrets, and large binaries out of agent-writable paths; use sandbox deny globs if needed

## 29. Daily / weekly rhythm

**Daily**

1. `grok -c` or resume named session for active milestone  
2. Attach `@docs/SESSION-HANDOFF.md` (do not rely on memory alone)  
3. One milestone slice with checklist prompt  
4. Verify → `/project-complete` → commit → `/flush`
5. Glance `/usage` and `/context` if the day was heavy  

**Weekly**

1. `/dream` if memory is noisy; prune stale `/remember` entries  
2. Prune dead sessions (`/resume` delete or dashboard)  
3. Update ROADMAP; clear abandoned worktrees  
4. `grok update` + re-skim `/release-notes` for behavior changes  
5. `grok inspect` after adding agents/skills/MCP  

---

# Part V — Anti-laziness and completeness (required)

## 30. Known product gaps (plan around them)

| Gap | Mitigation |
|-----|------------|
| No universal multi-part acceptance gate | Verify commands + `/project-complete`; careful Stop hooks only |
| Generator can overrate its own work | Use `/review`, `/goal` verification, or an independent read-only reviewer for risky changes |
| Plan mode doesn’t gate subagent writes | Use explore/plan / read-only project agents while planning |
| Compaction can omit important detail | Explicit `/flush` + SESSION-HANDOFF before intentional cuts; do not rely only on auto-flush |
| Over-delegation wastes context/credits | Default-deny spawn; watch `/usage` |
| Subagents cannot nest | Fan-out only from root conductor |
| Experimental memory can go stale | Prefer handoff file + `/flush`; treat memory as hints |
| Stop hook on STATUS:complete thrash | See §21 warning — do not use naively |

## 31. Completion ritual (agent + you)

**Agent (force via AGENTS.md):**

1. Checklist vs original ask  
2. Evidence for each item  
3. Project build/test/lint + `/project-complete` when code/docs changed
4. Update SESSION-HANDOFF  

**You (human QA):**

1. Skim final message for “I did X” without X existing  
2. Run the verify commands yourself if the agent skipped them; invoke `/project-complete` for the evidence checklist
3. If agent under-delivered: reply with **only** the missing checklist items — don’t restart the whole project narrative  

## 32. Phrases that force full delivery

Use when Grok is drifting:

```text
Re-read my original message. List every requirement. Mark DONE/MISSING with evidence. Finish all MISSING before stopping. Do not summarize as complete until the list is all DONE. Then run project verification and /project-complete.
```

```text
You stopped early. Continue from the incomplete items only. No new scope.
```

## 33. Anti-patterns (do not)

| Anti-pattern | Why it hurts |
|--------------|--------------|
| One mega-session for the whole project | Context rot; compaction amnesia |
| Fat multi-role `AGENTS.md` | Noise, conflicts, ignored conditionals |
| Spawning 3 writers “for speed” | Merge thrash + rework + cost |
| Expecting child agents to spawn helpers | Depth limit = 1; fails |
| Relying on memory without SESSION-HANDOFF | Stale/incomplete recall |
| Always-approve with no deny rules | Destructive bash risk |
| Stop hook requiring STATUS:complete every turn | Turn thrash mid-milestone |
| Skipping verification and `/project-complete` on multi-part asks | False “done” (the product does not universally auto-accept work) |
| Mixing Codex role TOMLs and Grok agent `.md` as one format | Wrong harness loads the wrong files |
| Deleting failing tests to “go green” | Breaks behavioral floor; classic agent failure |
| Fixing a wrong architecture with more chat | Revert → refine plan → re-run is usually faster |
| Fat AGENTS.md of unread prose | Research: noisy context can *hurt* success; keep short |

---

## 34. Industry patterns for agentic coding (external research, 2025–2026)

Synthesized from public sources (Cursor agent best practices, Addy Osmani long-running agents, Anthropic long-running harness writing, [agents.md](https://agents.md/) ecosystem guidance, CodeScene agentic quality patterns, multi-agent worktree practice). Map: **already in this playbook** vs **add if you want more leverage**.

### 34.1 Already covered well (keep)

| Industry pattern | In this playbook |
|------------------|------------------|
| Thin shared rules + nested package rules | §7, §7.1, §19 |
| Plan before ambiguous builds | §10, §23 |
| Fresh session / compact + disk handoff | §3, §25–§27 |
| Worktree isolation for parallel writers | §18b, §26 |
| Conductor + specialized workers | §5, §7.1, §19a |
| Separate review from implement | §19a reviewer; D6-style acceptance |
| Completeness checklists / anti false-done | §24, §30–§32 |
| Hooks for verify / stop discipline | §12, §21 |
| Default-deny spawn; cost awareness | §26, §30 |
| Human review of AI diffs | §31 |

### 34.2 High-value additions (use these)

#### A. Outer “Ralph loop” (filesystem is the memory)

Industry pattern: agent is **amnesiac each iteration**; durable state is on disk.

```text
loop:
  1. Read FEATURE-LIST.md / task queue — pick next unfinished item
  2. Read SESSION-HANDOFF.md + tail of progress.txt
  3. Fresh Grok session (or /new) with @ those files
  4. Implement ONE unit; run verify
  5. Append to progress.txt; check off feature; commit
  6. If agent claims done, re-check FEATURE-LIST — do not stop while unchecked items remain
```

Maps to Grok: `/loop` or shell + `grok -p`/`-c`, plus `docs/FEATURE-LIST.md` + `progress.txt` + handoff. Stronger than handoff alone for multi-hour/overnight work.

#### B. Done-condition before code (feature list / acceptance file)

Before any long run: external file of **testable** checkboxes the agent cannot quietly redefine. Anthropic-style `feature-list.json` / our `FEATURE-LIST.md`. Put acceptance in SESSION-HANDOFF *and* a living feature list for multi-session epics.

#### C. Test ratchet + TDD when behavior is the goal

1. Agent writes **failing** tests for the behavior (no implementation yet).  
2. You accept tests; commit.  
3. Agent implements until green **without editing tests**.  
4. **Never** delete/skip tests to pass (encode in AGENTS.md — now in §19).

#### D. Generator ≠ evaluator (planner / worker / judge)

Cursor/Anthropic: planners emit tasks, workers implement, **judges** decide if iteration is finished. Our reviewer is generation-adjacent; for long runs, treat **acceptance** as a separate pass (human, `/review`, `/goal` verification, or a dedicated reviewer session that cannot edit product code). Self-grading is systematically over-optimistic.

#### E. Revert + replan beats chat-repair

If the agent built the wrong thing: `/rewind` or git reset to plan baseline, **edit the plan**, re-run. Faster than piling corrective prompts on a confused context (Cursor practice).

#### F. Verify-until-green Stop loop (bounded)

Better than STATUS:complete thrash: Stop hook runs typecheck/tests; if fail and `loop_count < N`, return follow-up “continue fixing.” Cap iterations (e.g. 5). Cursor “grind until tests pass” pattern. Prefer this over handoff STATUS gates mid-milestone.

#### G. Commit every meaningful unit

Git as coordination substrate for long runs and parallel agents: small commits after each feature checkbox. Enables resume, review, and worktree merges.

#### H. Earned AGENTS.md only

[agents.md](https://agents.md/) + practitioners: short checklist, **every line earned by a real agent failure**, progressive disclosure (link to canonical files, don’t paste style guides). Research debate: bloated AGENTS.md can *reduce* success; update when agents fail, re-test the same task.

#### I. Quality / risk feedback in the loop

CodeScene-style: agents lack maintainability sense. Practical Grok version without new vendors:

- Mandatory lint/typecheck after edit series  
- Prefer small modules; refactor “hot” messy files **before** agent feature work  
- Optional: quality MCP (Code Health, Semgrep, etc.) if you adopt one  
- Coverage as **regression gate** on PRs, not a vanity target agents game  

#### J. Budgets and circuit breakers

Long runs need: token/time/tool-call caps, max Stop-loop iterations, max spawns per milestone, `/usage` checks. Without them, overnight agents burn credits quietly (Osmani / industry consensus).

#### K. Alignment drift defense

Each new session: re-read original goal + FEATURE-LIST first line of handoff. Compaction and multi-day runs dilute the original ask.

#### L. Parallel “same problem, pick best” (optional, expensive)

Cursor best-of-N: multiple models/agents same prompt in worktrees, human or judge picks winner. Use only on hard ambiguous design problems—not default.

#### M. Product/ops MCP when the work is not only code

Sentry, GitHub, browser/screenshot, design (Figma), Datadog — agent debugs production and implements UI against visual truth. Add MCP only when the project actually needs it (folder trust + secrets hygiene).

#### N. Atomic task claim for parallel top-level agents

If two dashboard agents share a task board, use claim files or exclusive milestone ownership so two agents don’t implement the same item (community worktree lock pattern).

### 34.3 Nice-to-have / Grok-specific mapping

| Pattern | Grok mechanism |
|---------|----------------|
| Cloud overnight agent | Headless `grok -p` on always-on host, or keep laptop awake; no first-party “cloud agent” required |
| Notifications when done | Config notification providers / OS notify (see Grok config) |
| Design → code | Paste image / path into prompt; browser tools if available |
| Issue → PR skill | Project skill: `gh issue view` → implement → `gh pr create` |
| Init agent once | First session writes FEATURE-LIST + init notes; later sessions only code |

### 34.4 What not to over-import

- Enterprise agent fleets / A2A registries — overkill for repo coding  
- Always-on multi-agent orchestration platforms unless you hit real parallel bottlenecks  
- Huge always-on rules files “just in case”  
- Unbounded Stop loops without `MAX_ITERATIONS`  

### 34.5 Suggested minimal upgrade to an existing long project

1. Add `docs/FEATURE-LIST.md` (checkboxes) + append-only `docs/progress.txt`.  
2. Add **test ratchet** line to AGENTS.md (already in §19 template).  
3. Prefer **TDD** for behavior-heavy milestones.  
4. After wrong builds: **revert + replan**, not endless repair chat.  
5. Optional: bounded Stop hook on **verify green** (not STATUS:complete).  
6. Commit after each feature checkbox; `/flush` + handoff at session cut.  
7. Only grow AGENTS.md when an agent fails the same way twice.

---

# Part VI — Copy-paste command cheatsheet

```bash
# Start / resume
grok
grok -c
grok --resume <session-id>
grok --cwd ~/proj --effort high
grok --worktree=feat-auth --ref main "implement auth slice"

# Trusted automation (still use deny rules)
grok --always-approve
grok -p "…" --always-approve --output-format json --max-turns 50
grok -p "…" -r <session-id> --output-format json   # multi-step pipeline
grok -p "…" --no-subagents                         # root-only automation

# Named project agent (project must be trusted)
grok --agent conductor

# Sandbox
grok --sandbox workspace

# Memory
export GROK_MEMORY=1

# Inspect project loadout
grok inspect
grok sessions list
grok sessions search "auth"

# Update CLI
grok update
```

```text
# In-session
/plan …
/view-plan
/compact keep architecture decisions and open bugs
/flush
/remember …
/project-complete
/review
/goal …
/loop 30m …
/dashboard
/config-agents
/session-info
/context
/usage
/rename m3-payments
```

---

# Part VII — Per-project startup checklist

Print and tick when opening a **new** long-running project:

- [ ] Thin shared `AGENTS.md` (completeness + verify + handoff) — **not** a multi-role novel  
- [ ] If multi-agent: `.grok/agents/*.md` per role with `agents_md: true` (§7.1, §19a); names do not blindly shadow built-ins  
- [ ] Project `.grok/config.toml` deny rules for destructive git/bash (§18a)  
- [ ] `docs/SESSION-HANDOFF.md`, `ROADMAP.md`, `DECISIONS.md`  
- [ ] `.grok/skills/project-complete/` (optional but recommended)  
- [ ] Memory enabled globally or for this workstream  
- [ ] `grok inspect` shows expected skills, **agents**, and rules  
- [ ] Folder trusted, then a fresh session started so project AGENTS/config load; project skills/hooks/MCP are visible
- [ ] First session: architecture or roadmap only; `/flush` at end  
- [ ] Naming convention for sessions: `/rename m1-auth-scaffold`  
- [ ] Know conductor→worker topology (no nested spawns)  

---

# Part VIII — Feature index (quick reference)

| Area | Features |
|------|----------|
| Core loop | Tools, permissions, todos, ask-user |
| Context | Compact, auto-compact, context UI, rewind |
| Parallel | Subagents, worktrees, dashboard, fork |
| Persistence | Sessions, memory, handoff docs |
| Structure | Plan mode, goals, workflows, deep-research |
| Automation | Hooks, /loop, monitor, scheduler, headless |
| Extensibility | Skills, MCP, plugins, LSP, personas, agents |
| Safety | Deny rules, sandbox, hooks, folder trust |
| Ops | /usage, /doctor, /feedback, release notes |

## Official guide coverage map (all user-guide docs)

Every guide under `~/.grok/docs/user-guide/` was inventoried for this playbook. Depth matches long-running relevance:

| Guide | Covered here | Long-run priority |
|-------|--------------|-------------------|
| 01 Getting started | §1, install/run | Medium |
| 02 Authentication | §1 (browser / API key) | Medium |
| 03 Keyboard shortcuts | §16 essentials | Medium |
| 04 Slash commands | Throughout + §6–15 | High |
| 05 Configuration | §18, config snippets | High |
| 06 Theming | Not expanded (UI-only) | Low |
| 07 MCP servers | §13 | High when integrations needed |
| 08 Skills | §8 | High |
| 09 Plugins | §13 | Medium |
| 10 Hooks | §12, §21 | High |
| 11 Custom models | §14 pointer | Low–medium |
| 12 Project rules | §7, §19 | **Critical** |
| 13 Memory | §9, §22 | **Critical** |
| 14 Headless mode | §15 | High for CI/automation |
| 15 Agent mode (ACP) | §1 | Medium (IDE) |
| 16 Subagents | §5, §26 | **Critical** |
| 17 Sessions | §6, §25 | **Critical** |
| 18 Sandbox | §12 | High for untrusted/safety |
| 19 Plan mode | §10 | High |
| 20 Background tasks | §4, §11 | High |
| 21 Terminal support | Doctor / UX only | Low |
| 22 Permissions | §12 | **Critical** |
| 23 Dashboard | §5, §16 | High multi-agent |
| 24 Monitoring usage | `/usage`; external OTEL optional | Medium |

Full docs: `~/.grok/docs/user-guide/` or in-TUI `/docs`. Online: `https://docs.x.ai/build/overview` via `/docs web`.

## Slash-command families (complete set from docs)

| Family | Commands |
|--------|----------|
| Session | `/new`, `/resume`, `/dashboard`, `/compact`, `/context`, `/session-info`, `/fork`, `/rewind`, `/edit-prompt`, `/copy`, `/export`, `/quit`, `/home`, `/delete`, `/rename` |
| Model/mode | `/model`, `/effort`, `/always-approve`, `/auto`, `/multiline`, `/history`, `/compact-mode`, `/vim-mode`, `/minimal`, `/fullscreen`, `/plan`, `/view-plan` |
| Memory | `/memory`, `/flush`, `/dream`, `/remember` |
| Extensions | `/hooks`, `/plugins`, `/marketplace`, `/skills`, `/mcps` |
| Media | `/imagine`, `/imagine-video` |
| Scheduling | `/loop` |
| Goals/workflows | `/goal`, `/deep-research`, `/workflow`, `/workflows` |
| Other | `/theme`, `/feedback`, `/btw`, `/doctor`, `/release-notes`, `/docs`, `/tutorial`, `/import-claude` |
| Agents | `/config-agents`, `/personas` |
| Account | `/login`, `/logout`, `/usage`, `/privacy` |
| Config UI | `/settings`, `/timestamps` |
| Skills | any `user-invocable` skill as `/name` |

## Built-in agent types (complete)

`general-purpose`, `explore`, `plan` (+ custom under `.grok/agents/` / `~/.grok/agents/`).

## Multi-agent layering (quick)

| Shared | Per role | Optional overlays |
|--------|----------|-------------------|
| `AGENTS.md` | `.grok/agents/<role>.md` | personas, roles, skills |
| Completeness, verify, security | Identity, tools, output contract | Tone, I/O, procedures |

See **§7.1** and **§19a**.

---

# Part IX — Self-check: did this document satisfy the request?

| You asked | Delivered? | Where |
|-----------|------------|--------|
| Full review of Grok Build features | Yes | Parts I–II, VIII |
| Tools and how it works | Yes | §§2–4 tool tables, turn model, sessions, subagents |
| MD file of instructions | Yes | This file |
| Usable for **every** Grok Build project | Yes | Part III templates + Part VII checklist |
| Optimize for **long-running** projects | Yes | Parts III–V (milestones, compact, memory, parallel, handoff) |
| Not lazy / double-check completeness | Yes | Part V + this checklist |

**Sources consulted:** current xAI documentation for [Grok 4.7](https://docs.x.ai/developers/grok-4-7), [Build settings](https://docs.x.ai/build/settings), [skills/plugins](https://docs.x.ai/build/features/skills-plugins-marketplaces), [subagents](https://docs.x.ai/build/features/subagents), [permissions](https://docs.x.ai/build/features/permissions), [modes and commands](https://docs.x.ai/build/modes-and-commands), [headless scripting](https://docs.x.ai/build/cli/headless-scripting), [project rules](https://docs.x.ai/build/features/project-rules), and [hooks](https://docs.x.ai/build/features/hooks); plus the installed 1.0.41 user guide, `grok inspect`, `grok --help`, and the live Build model catalog.

**Not a substitute for:** reading `/docs` after major CLI upgrades — re-verify after `grok update`.

---

> [!tip] Install this playbook globally
> Copy to `~/.grok/AGENTS.md` (short pointer) + keep the full playbook in a personal notes repo, **or** vendor a shortened “completeness + session hygiene” block into every project `AGENTS.md` and link here for depth.
>
> Multi-agent repos: keep global/user rules shared; put role files in **project** `.grok/agents/` so teammates share the same conductor/explorer/implementer/reviewer set.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-10-15 | Review hardening: staged rollback-safe install, fail-before-write AGENTS validation, symlink-safe resets, package-manager-aware verify commands, and explicit warning when an existing project config receives no GLRP deny rules |
| 2026-10-13 | Grok 4.7 / Build 1.0.41 migration: current CLI and subagent fields, canonical memory/agent/headless commands, trust/reload lifecycle, Build-vs-API context distinction, project-complete verification, portable and non-clobbering scaffold |
| 2026-08-01 | Initial playbook: feature map + long-running protocol |
| 2026-08-02 | Multi-agent findings: thin `AGENTS.md` vs `.grok/agents/`; §7.1 decision table; scaffold + §19a templates; checklist updated |
| 2026-08-02 | Completeness pass: subagent depth=1, name shadowing, two_pass_compaction, project deny config, worktrees §18b, Stop-hook warning, attach handoff, cost note, anti-patterns §33 |
| 2026-08-02 | Industry research §34: Ralph loop, feature list, test ratchet, TDD, judge separation, revert+replan, budgets, earned AGENTS.md; AGENTS template + scaffold updated |
