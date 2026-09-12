# Working rules for this repository

## Session hygiene (token cost)

Usage limits count tokens, and the entire conversation is re-sent on every
turn. Long, mixed-topic sessions are the main source of runaway cost.

- **One topic per session.** Start a new session (`/clear`) when the subject
  changes. Do not use `/compact` to carry unrelated work forward — the summary
  becomes a new per-turn baseline that is paid for on every subsequent turn.
- **Read a file once.** Do not re-read a file to verify an edit; `Edit` and
  `Write` fail loudly if they did not apply.
- **Use Grep/Glob over dumping whole files.** Read only the lines needed.
- **Do not spawn subagents unless asked.** Each one starts cold and re-derives
  context that already exists here.
- **Model:** Opus for planning and architecture; `/model sonnet` for routine
  edits, README work and git operations.

`.claude/settings.json` trims the per-turn skill listing: skills irrelevant to
this repository are set to `user-invocable-only`, so they cost no context but
are still runnable by typing `/<name>`. Set one back to `on` if the model
should discover it automatically.

## Cinema 4D

Ground-truth facts about the C4D scripting environment (measured on
2026.3.0.4) are in `DESIGN.md`. Do not re-derive them, and do not trust
recalled API knowledge over what the probe scripts in `tools/` measured.
