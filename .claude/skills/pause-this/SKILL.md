---
name: pause-this
description: Mid-session pause. Checks the build, commits WIP, and notes the pause point in the session file. Use when you need to walk away mid-task without closing the session. Follow up with /restart-this to resume.
tools: Read, Edit, Write, Bash, Glob, Grep
---

You are executing a mid-session pause.

## Step 0 — Locate the open session

```
SESSION_FILE=$(grep -l "^status: open" .sessions-worktree/sessions/*.md 2>/dev/null | head -1)
```

If found: NEW MODE — pause note goes in the session file's Context section (on the sessions branch).
Otherwise check `session-log.md` for `[open]`: LEGACY MODE — pause note goes there.

## Step 1 — Build check (conditional)

Look up the project's build check in `CLAUDE.md §Commands`. Run whatever is defined (e.g. `npm run build`, `cargo build`, `make`). If `CLAUDE.md §Commands` defines no build step, skip silently.

If the build fails: do NOT commit broken code. If you can't fix quickly, note the errors in the pause entry so the next sitting knows where to start.

## Step 2 — Commit WIP on the task branch

```
git add -A
git commit -m "WIP [phase/task] — [brief description of where things stand]"
```

Prefix with `WIP`. If nothing to commit, skip and say so. This commit goes to the **current task branch** — NOT to the sessions branch.

## Step 3 — Note the pause in the session file (sessions branch)

Append a pause line to the session file's `**Context:**` section:

```
**[PAUSED HH:MM UTC]** Working on: [task]. Left off at: [specific file/function/step]. Next: [exactly what to do when resuming].
```

Commit + push from inside the worktree:
```
cd .sessions-worktree
git add sessions/$(basename "$SESSION_FILE")
git commit -m "Pause note for Session <N>"
git push origin sessions
cd ..
```

Do not close the session. Do not fill `ended:` / `points:`. Status remains `open`.

## Step 4 — Confirm

Tell the user:
- What was committed on the task branch (or that nothing was)
- What the pause note says
- To run `/restart-this` when ready to resume
