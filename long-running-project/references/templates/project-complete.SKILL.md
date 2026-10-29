---
name: project-complete
description: >
  End-of-turn completeness ritual for long-running projects. Use before finishing
  multi-part requests, implementation, review, or research deliverables. Also use
  when the user says done?, finish, ship, or complete the ask.
user-invocable: true
---

# Completeness ritual

1. Quote the user's original requirements as a checklist.
2. For each item: DONE with evidence path/command, or MISSING.
3. If any MISSING: continue working — do not end the turn.
4. If all DONE and code changed: run the project's build/test/lint commands. For risky work, also run `/review` or use an independent reviewer.
5. Update `docs/SESSION-HANDOFF.md`.
6. Update `docs/FEATURE-LIST.md` / append `docs/progress.txt` when applicable.
7. Only then write the final summary.
