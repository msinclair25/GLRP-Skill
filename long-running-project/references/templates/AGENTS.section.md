<!-- LONG-RUNNING-PROJECT:START -->
## Long-running project protocol (managed by `/long-running-project`)

### Completeness (non-negotiable)
- Multi-part user requests are incomplete until EVERY part is done at full depth.
- Before ending a turn, re-read the latest user message and list unmet requirements.
- If completeness conflicts with brevity, completeness wins.
- After any multi-part or code task, run the project verify commands, then invoke `/project-complete`.

### Session hygiene
- Prefer milestone-sized work, not infinite threads.
- Maintain `docs/SESSION-HANDOFF.md`: goal, done, open risks, next 3 steps, key paths, commands.
- Maintain `docs/FEATURE-LIST.md` checkboxes for multi-session epics; append notes to `docs/progress.txt`.
- Before `/compact` or `/new`: `/flush` memory (if enabled) and update SESSION-HANDOFF.
- One coherent milestone per session when practical; start fresh after acceptance.
- On resume, attach `@docs/SESSION-HANDOFF.md` (and FEATURE-LIST if present).

### Delegation
- Default-deny subagents: spawn only for independent, bounded, provable work.
- Prefer project agents under `.grok/agents/` (`explorer`, `implementer`, `reviewer`) or built-in `explore`/`plan`.
- Max one writer set of paths at a time; use worktree isolation for parallel writers.
- Subagents cannot nest (depth 1): only the root/conductor spawns children.
- Return compact evidence (commands, paths, results) — not raw logs.
- Role details live in `.grok/agents/` — do not restate per-role prompts here.

### Quality
- Do not claim done without running the project's verify commands (below).
- **Test ratchet:** never delete, skip, or weaken tests to make the suite green. Fix code or mark BLOCKED.
- Prefer smallest change that meets the request.
- Prefer pointers to canonical files over pasting long style guides.

### Verify commands
- Build: `<!-- VERIFY_BUILD -->` (fill in)
- Test: `<!-- VERIFY_TEST -->` (fill in)
- Lint / typecheck: `<!-- VERIFY_LINT -->` (fill in)
- After a series of edits, run typecheck/lint before declaring done.

### Living rules
- Only add durable rules when an agent *failed* for a real reason; keep every line earned.
- Point to `docs/` for deep architecture; keep this file short.

### Do not
- Invent secrets or commit `.env`
- Force-push without explicit ask
- Expand scope beyond the request without asking
<!-- LONG-RUNNING-PROJECT:END -->
