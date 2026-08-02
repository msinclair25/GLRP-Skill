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
4. If all DONE: run `/check-work` when code changed; update `docs/SESSION-HANDOFF.md`.
5. Update `docs/FEATURE-LIST.md` / append `docs/progress.txt` when applicable.
6. Only then write the final summary.
