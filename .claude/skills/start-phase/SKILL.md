---
name: start-phase
description: Materialize a phase from PROJECT_PLAN.md into GitHub Issues. Reads the phase's task rows, creates one Issue per task (with phase:N and points:X labels), writes issue numbers back into PROJECT_PLAN.md, and adds them to the project board. Run at phase boundaries — paired with /retro at phase end.
tools: Read, Edit, Write, Bash, Glob, Grep
---

You are materializing a phase from `docs/PROJECT_PLAN.md` into GitHub Issues.

## Step 0 — Determine which phase

If the user passed a phase number as an argument (`/start-phase 1`), use that.

Otherwise: find the lowest phase in PROJECT_PLAN.md whose tasks are all unstarted (no `[#N](url)` issue links yet). Confirm with the user before proceeding:

> "Materialize Phase **N** — *<phase name>* — into Issues? (Y / cancel / different phase)"

Wait for confirmation.

## Step 1 — Verify prerequisites

Run these checks; abort with a clear message if any fail:
- `gh auth status` — must be authenticated
- `gh repo view --json nameWithOwner` — must be in a GitHub repo
- `git status --porcelain` — working tree must be clean (no uncommitted edits to PROJECT_PLAN.md before the phase materialization writes issue links)
- `gh label list --limit 100` — verify required labels exist; if missing, create them:
  - `phase:0` through `phase:9` (or just the one for this phase)
  - `points:1`, `points:2`, `points:3`, `points:5`, `points:8`
  - `blocked`
  - Use distinguishable colors. Skip silently if a label already exists.

## Step 2 — Parse phase tasks from PROJECT_PLAN.md

Extract the phase block (between `## Phase N` heading and the next `##` heading). Parse the task table — each row should have: id, description, points, status. Format may vary; common shape:

```
| 1.1 | Task description | 3 | TBD |
```

Capture: `TASK_ID`, `DESCRIPTION`, `POINTS`, `STATUS`. Skip rows where status is already `[x]` or already has an issue link.

If the parser fails on a row, surface it to the user and ask how to proceed (skip / fix manually / abort).

## Step 3 — Create one Issue per task

For each parsed task:

```
gh issue create \
  --title "Phase N.X — <description>" \
  --body "<body>" \
  --label "phase:<N>,points:<P>"
```

**Body template:**
```
**Task ID:** <TASK_ID>
**Phase:** <N>
**Points:** <P>
**From:** [docs/PROJECT_PLAN.md](../../docs/PROJECT_PLAN.md#phase-<N>)

## Acceptance criteria

[Pull from PROJECT_PLAN.md if present in the row's Notes column, else leave a placeholder for the user to fill in.]

## Notes

[Any inline notes from the PROJECT_PLAN.md row — dependencies, blockers, etc.]
```

Capture each created issue's number. If `gh issue create` fails partway through, surface the failure, list which issues were created so far, and ask the user whether to retry or abort.

## Step 4 — Write issue numbers back into PROJECT_PLAN.md

For each task row, replace the status cell (`TBD`, `[ ]`, etc.) with a link to the issue:

```
| 1.1 | Task description | 3 | [#42](https://github.com/owner/repo/issues/42) |
```

This is a one-time write at phase start. The file goes read-only until `/retro`.

## Step 5 — Add to project board (optional)

If the project has a GitHub Project board configured (check via `gh project list --owner <owner>`), add each new issue:

```
gh project item-add <project-number> --owner <owner> --url <issue-url>
```

If no project board exists, skip silently. The user can add the board later and bulk-add via the GitHub UI.

## Step 6 — Commit and push

```
git add docs/PROJECT_PLAN.md
git commit -m "Materialize Phase N — <count> issues created"
git push origin <BRANCH>
```

## Step 7 — Summary

Print:
```
Phase N materialized.
Created issues: #N1, #N2, ... (count: X)
Total points: Y
Project board: <link or "none configured">

Next: pick the first issue and cut a branch — `git checkout -b task/N.X-description`
At phase end, run `/retro`.
```
