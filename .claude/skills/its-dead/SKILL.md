---
name: its-dead
description: Session end. Stamps `ended:` on the open session file, tallies total points from per-task blocks, displays wall_clock to screen for gut-check, commits + pushes the sessions branch. No time math, no version bump, no merge handshake — those moved to `/retro` per DEC-S013. Run once at the end of a Claude window after every task's `/kill-this` has shipped its PR.
tools: Read, Edit, Write, Bash, Glob, Grep
---

You are closing the session. Under DEC-S013, this is a one-action skill: stamp `ended:`, write `status: closed`, commit + push to the orphan `sessions` branch. All time math (wall_clock and active = wall_clock − breaks, via transcript break inference) and version bumps moved to `/retro`. The session file becomes atomic — never modified after this runs.

## Step 0 — Locate the open session (on the sessions worktree)

```
SESSION_FILE=$(grep -l "^status: open" .sessions-worktree/sessions/*.md 2>/dev/null | head -1)
```

If found: NEW MODE. Continue.

If not: try legacy `session-log.md` on the current branch. If found: LEGACY MODE — Step 4 still applies; everything else simplifies. If neither: STOP and ask the user how to proceed.

## Step 1 — Stamp `ended:`

```
END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

Edit `$SESSION_FILE` frontmatter:
- `ended: <END_UTC>`
- `status: closed`

Do **not** write `wall_clock`, `active`, `breaks`, `duration`, or any time-derived field. Time math is `/retro`'s job (DEC-S013).

## Step 2 — Tally total points

Scan the body for per-task blocks (one per `/kill-this`):

```
grep -A 5 "^## Task " "$SESSION_FILE" | grep "Points:" | grep -oE "[0-9]+"
```

Sum and write the total into the frontmatter:
- `points: <SUM>`

If no `## Task <N>` blocks exist (a session that ran `/its-alive` and `/its-dead` with no `/kill-this` in between), `points: 0`. No warning — sometimes the work is exploration that didn't ship.

## Step 3 — Append session-wide Context (optional)

If the user wants to add session-wide Next Steps or Context notes that aren't per-task, prompt:

```
Anything to add to **Next Steps** (what to pick up next session)?
Anything for **Context** (gotchas, patterns, hidden constraints)?
```

Append to the existing `**Next Steps:**` and `**Context:**` sections at the bottom of the file. These sections cover the session as a whole; per-task notes live inside their own `## Task <N>` block.

## Step 4 — Display wall_clock to screen (gut-check only — NOT persisted)

Compute on screen for the user's sanity check:

```
WALL_CLOCK = (END_UTC − started) in hours, rounded to nearest 0.083h (5 min).
```

Display:
```
Wall clock: Xh Ym  (started <ISO_STARTED>, ended <END_UTC>)
PRs this session: #N1, #N2, ...   (from pr_numbers list)
Total points: <SUM>
```

**Do not write this to the file.** The user verifies; `/retro` computes the persisted numbers at phase end.

If the wall_clock looks wildly wrong (e.g. user expected 2h, sees 9h because of an overnight gap), the user can record a note in the Context section. The actual active time will be inferred at retro (wall_clock minus transcript break gaps); the displayed wall_clock is just the raw delta.

## Step 5 — Commit + push the sessions branch (from the worktree)

```
git -C .sessions-worktree add sessions/$(basename "$SESSION_FILE")
git -C .sessions-worktree commit -m "Close Session <N>"
git -C .sessions-worktree push origin sessions
```

No version bump. No CHANGELOG. No tag. No branch cleanup (task branches and their PRs are managed by the user per-task at `/kill-this` time and via the GitHub merge button).

**LEGACY MODE (no `.sessions-worktree/`, working from `session-log.md`):** stage + commit + push `session-log.md` to the current branch. Skip the worktree-specific commands.

## Step 6 — Closing summary

```
Session <N> closed.
Wall clock (raw): Xh Ym       <- gut-check only, not persisted
PRs: #N1, #N2, ...            <- still need merging if any are still OPEN
Points (per-task sum): <S>

The session file is now atomic — no further writes will modify it.
Time math (active = wall_clock − breaks, via break inference) + version bump will run at /retro.
```

If any `pr_numbers` PR is still OPEN, append:
```
⚠ PRs still OPEN: #N1, #N2. Merge them whenever — order and timing don't matter for retro math.
```

If on a phase-rituals project, append:
```
Phase progress: gh issue list --label phase:current --state open
```

## Notes

- Sanity check at close: the displayed wall_clock is `ended − started`. If it includes overnight or away-from-desk time, that's correct — `/retro` will subtract break gaps later. The screen number isn't the final number.
- No interactive merge handshake (DEC-S012 had one). Under DEC-S013, the user merges PRs whenever convenient — before `/its-dead`, after, doesn't matter. Retro reads GitHub for merge timestamps at retro time.
- Atomicity guarantee: once `status: closed` is set and the file is pushed, this skill is done. No subsequent skill modifies this file. `/its-alive`'s old Step 7.5 backfill is gone (DEC-S013).
