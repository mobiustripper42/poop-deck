---
name: restart-this
description: Resume after a mid-session pause. Reloads context from the session file and project plan, then presents a focused briefing so work can continue from exactly where it stopped. Does not open a new session.
tools: Read, Bash, Glob, Grep
---

You are resuming a paused session. Do NOT open a new session entry — this is a continuation of the existing open session.

## Step 0 — Locate the open session

```
SESSION_FILE=$(grep -l "^status: open" .sessions-worktree/sessions/*.md 2>/dev/null | head -1)
```

If found: NEW MODE.
Otherwise check `session-log.md` for `[open]`: LEGACY MODE.

If neither found: stop and tell the user there's no open session to resume — they probably want `/its-alive`.

## Step 1 — Stamp the resume time

`RESUME_UTC=$(date -u +%H:%M)`

Append to the session file (in the worktree) immediately after the most recent `[PAUSED ...]` line:

```
**[RESUMED HH:MM UTC]**
```

Commit + push from inside the worktree:
```
cd .sessions-worktree
git add sessions/$(basename "$SESSION_FILE")
git commit -m "Resume note for Session <N>"
git push origin sessions
cd ..
```

## Step 2 — Read the pause note

Locate the most recent `[PAUSED HH:MM UTC]` line. Extract:
- Task being worked on
- File / function / step left mid-work
- Immediate next action

## Step 3 — Read project state

Grep `docs/PROJECT_PLAN.md` for the current task context — phase, task ID, acceptance criteria. Do not read the whole file.

## Step 4 — Present resume briefing

```
Resuming Session <N> — paused HH:MM UTC, resumed HH:MM UTC
Branch: <BRANCH>
Session file: <SESSION_FILE> (or "session-log.md" in legacy mode)

Task: [task ID and name]
Left off at: [file/function/step]
Next action: [exactly what to do now]
```

Then say: **"Ready when you are."**

If the pause note is missing or unclear, ask the user where they left off before proceeding.
