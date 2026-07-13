---
name: retro
description: Phase-end retrospective. Closes the current phase. Under DEC-S013 retro owns the phase velocity math; under DEC-S026 that math is throughput (points per calendar week) computed from GitHub issue `closedAt` dates + `points:N` labels, plus an estimate-calibration tally — no session transcript is read. Marks PROJECT_PLAN.md `[x]`, reconciles drift, writes RETROSPECTIVES.md, runs version bumps (patch per merged PR + minor at phase close on dev projects), prompts retro notes. Optionally chains into `/start-phase`.
tools: Read, Edit, Write, Bash, Glob, Grep, Agent
---

You are running the phase-end retrospective. Work for this phase is complete (or you've decided to call it done and move scope).

Under DEC-S013 this skill **owns the phase velocity math** that used to live in `/its-dead` and **all version bumps** (patch per merge + minor at close). Under DEC-S026 that velocity math is **throughput + estimate calibration**, computed from GitHub issue dates + `points:N` labels — the transcript-based `active = wall − breaks` model is retired. Session files are atomic event logs; GitHub is the velocity data source.

## Step 0 — Identify the current phase

Find phase N as the **lowest phase number with any open issues** OR (if all closed) the highest phase with `[ ]` rows in PROJECT_PLAN.md but no `[x]` marks yet.

```
for phase in 0 1 2 3 4 5 6 7 8 9; do
  open=$(gh issue list --label "phase:$phase" --state open --json number -q 'length')
  if [ "$open" -gt 0 ]; then echo "Phase $phase has $open open issues"; break; fi
done
```

Confirm: "Run retro for Phase **N**?" Wait.

## Step 1 — Account for all phase issues

```
gh issue list --label "phase:<N>" --state all --json number,title,state,labels --limit 100
```

For each open issue, ask the user: "Move to next phase, leave open, or close as won't-do?"
- **Move:** swap `phase:N` → `phase:N+1`.
- **Leave open:** record in retro.
- **Close as won't-do:** `gh issue close <N> --reason "not planned" --comment "Closed at Phase N retro — descoped."`

## Step 2 — Phase throughput + estimate calibration (DEC-S026 — replaces transcript-based time math)

DEC-S026 retired the `active = wall_clock − breaks` model. **No session transcript is read in this step.** Two numbers come out of it, both from data GitHub already holds: the phase's **throughput** (points per calendar week) and an **estimate-calibration tally** (did the points hold their value). Fleet validation showed solo phases are burst-shaped — most clear inside a single calendar week — so throughput is a coarse capacity signal, not a precise rate; the calibration tally is what keeps the point unit honest.

Phase window: `phase_first_created` = first issue's `createdAt`, `phase_last_closed` = last issue's `closedAt`.

### Step 2.1 — Phase points + dates (GitHub only)

```
gh issue list --label "phase:<N>" --state closed --json number,createdAt,closedAt,labels --limit 200
```

- `phase_points` = Σ of each closed issue's `points:M` label value. Issues with **no** `points:` label are skipped — list them in the retro so they're visible; never guess a value.
- `phase_first_created` = min `createdAt`; `phase_last_closed` = max `closedAt`; `phase_span_days = (phase_last_closed − phase_first_created)` in days.

This keys the phase to issues, not PRs — robust to merging PRs in any order (DEC-S022). **Never re-pair PR-open → PR-merge to recover "effort"** — that window math is the exact bug DEC-S024 died on. Dates are not windows.

### Step 2.2 — Throughput (the headline)

```
phase_calendar_weeks = phase_span_days / 7
throughput           = phase_points / phase_calendar_weeks    # points per calendar week
```

- **If `phase_span_days < 7`** (phase opened and closed inside one week — a *burst* phase): do **not** quote a per-week rate. A sub-week denominator explodes it into nonsense (a phase done in an afternoon reads as hundreds of pts/wk). Record `throughput: burst (<7d) — <phase_points> pts over <phase_span_days>d` instead. Most solo phases land here; the point total + span is the honest record.
- **Companion (optional):** `active_weeks` = ISO weeks in the span containing ≥1 close; `active_throughput = phase_points / active_weeks` = intensity when actually shipping (strips idle/off weeks).

Throughput is capacity **including availability** — a slow week and an off week look identical. Correct for "when does the *next* phase ship," wrong for "at-keyboard speed." Never quote it as the latter. It is an active-time rate; a calendar forecast = throughput ÷ your real availability, which only you know.

### Step 2.3 — wall_clock (gut-check only — NOT a velocity)

`/its-dead` already displayed each session's `wall_clock = ended − started` on-screen as a sanity gut-check. That is its only role. **It is not aggregated, not divided by points, and not quoted as a velocity** — `wall_clock / point` is the number the guide forbids (it carries overnight gaps and idle). No transcript is read; no breaks are inferred; there is no `active_time`. (This is the DEC-S024 model being retired — see DEC-S026.)

### Step 2.4 — Estimate-calibration tally

Throughput alone rots: if points quietly shrink, "throughput" rises while nothing actually got faster. This tally is the guard, and it replaces the old per-session h/pt spread as the estimate-health signal.

From PROJECT_PLAN.md's estimate column + this phase's session notes:
- `re_estimated` = count of tasks whose points changed between original estimate and final (re-pointed mid-flight).
- `net_drift` = Σ(final points) − Σ(original points). Positive = tasks ran bigger than pointed (under-estimating); negative = smaller.

Record `re-estimated: <K> tasks, net drift: <±D> pts`. A stable point unit shows few re-estimates and near-zero net drift. Persistent positive drift = under-pointing; persistent **shrink alongside rising throughput** = point inflation — the failure mode throughput can't see on its own.

### Step 2.5 — Per-phase line for the retro

One phase row (there is no longer a per-session time table — the transcript that fed it is gone):

```
| Phase N | <phase_last_closed date> | <points> | <span_days>d | <throughput or "burst"> | <re_estimated> | <net_drift> | <sessions> | <PRs> |
```

`sessions` = count of session files in the window (reference only); `PRs` = merged PRs in the window. Hold these for Step 3.

## Step 3 — Phase metrics

From Step 2:
- `phase_points` — Σ `points:N` on closed phase issues (cross-check against PROJECT_PLAN's estimate column; flag mismatch).
- `throughput` — points per calendar week (or `burst` for sub-week phases). **The headline** — but never reported without the calibration tally beside it.
- `re_estimated` + `net_drift` — the estimate-calibration tally.
- `phase_sessions` = session-file count in the window; `phase_prs` = merged PRs in the window.

There is no `active`, no `breaks`, no `dev_time`/`review_time`, and no `h/pt` — all retired by DEC-S026.

## Step 4 — Update PROJECT_PLAN.md

Mark all closed phase tasks `[x]`. For each row:
```
| 1.1 | Task description | 3 | [x] [#42](url) |
```

Reconcile drift: issues with `phase:<N>` labels that don't appear in PROJECT_PLAN.md (added mid-phase). Add rows with status `[x] [#N](url)` and inline note `Added during P<N> retro`.

Update the velocity table at the top (DEC-S026 columns):
```
| Phase | Points | Span (d) | Throughput | Re-est'd | Net drift | Sessions |
|-------|--------|----------|------------|----------|-----------|----------|
| N     | <pts>  | <days>   | <pts/wk or burst> | <K> | <±D> | <count> |
```

Append one row per phase as they complete. **Don't rewrite history:** phases closed before DEC-S026 carry the retired `Wall / Breaks / Active / h-pt` columns — leave those rows as written and note the metric change inline (the full table migration is a separate deferred task).

## Step 5 — Prompt retro notes

Ask three questions, one at a time, capture verbatim:
1. **What worked?**
2. **What didn't?**
3. **What changes for next phase?**

## Step 5.5 — PM retro commentary

Invoke `@pm` (Sonnet) with the full retro context: phase number + name, metrics from Step 3 (throughput + calibration tally), user's verbatim answers, the phase line from Step 2.5, closed-issue list with descoped/moved notes, and `docs/RETROSPECTIVES.md` for cross-phase comparison. Let `@pm` read the session files themselves for in-the-trenches detail.

`@pm` returns 3–5 short paragraphs on pace, scope, patterns, a reaction to the user's answers (not a paraphrase), and a forward-looking note.

Show the commentary verbatim:
> **PM read on Phase N:**
>
> <commentary>
>
> Use (a), edit (e), or skip (s)?

- **Use:** carry forward.
- **Edit:** ask "What would you change?" — apply edits, carry forward.
- **Skip:** omit the section from RETROSPECTIVES.md.

## Step 6 — Append to RETROSPECTIVES.md

Read `docs/RETROSPECTIVES.md` first (Edit requires a prior Read). If it doesn't exist, create it with Write and the header `# Retrospectives\n\n`. Otherwise Edit the file by replacing the `# Retrospectives\n\n` header with `# Retrospectives\n\n## Phase <N> — <YYYY-MM-DD>\n\n...full block...\n\n` so the new phase lands at the top. Block template:

```
## Phase <N> — <YYYY-MM-DD>

**Points:** <points completed> / <planned> (<%>)
**Span:** <span_days> days (<first_created> → <last_closed>)
**Throughput:** <pts/wk> pts/calendar-week  ← headline (or: `burst — <pts> pts in <days>d` for sub-week phases)
**Estimate calibration:** <K> tasks re-estimated, net drift <±D> pts  ← keeps the point unit honest
**Sessions:** <count>   **PRs merged:** <count>
**Issues:** <created> created, <closed> closed, <moved> moved to Phase <N+1>

### Phase throughput line
| Phase | Date | Points | Span(d) | Throughput | Re-est'd | Net drift | Sessions | PRs |
|-------|------|--------|---------|------------|----------|-----------|----------|-----|
| <row> | ...  | ...    | ...     | ...        | ...      | ...       | ...      | ... |

### What worked
- <verbatim>

### What didn't
- <verbatim>

### Changes for next phase
- <verbatim>

### Scope changes
- [Tasks added mid-phase, moved out, descoped]

### PM read
<commentary from Step 5.5, verbatim or edited — omit section if skipped>
```

## Step 7 — Commit (sessions branch updates are read-only here)

Session files were already finalized by `/its-dead` and are not modified by this skill — DEC-S013 atomicity.

```
git add docs/PROJECT_PLAN.md docs/RETROSPECTIVES.md
git commit -m "Phase <N> retro — <points> pts, throughput <pts/wk or burst>, drift <±D>"
git push origin <BRANCH>
```

## Step 8 — Version bumps (dev projects only — DEC-S013 moved patch bumps from `/its-dead` here)

Run only if `package.json` exists at the repo root (dev-project signal — DEC-S007).

Resolve working branch — always the active trunk (DEC-S022):
```
WORKING_BRANCH=main
```
Bumps and tags land on `main` directly; `production` (if any) only moves at `/promote-production`.

If `BRANCH != $WORKING_BRANCH`: STOP. Tell the user "Switch to `$WORKING_BRANCH` and re-run /retro." Wait.

### Step 8.1 — Enumerate merged PRs in the phase window

```
gh pr list --state merged --search "merged:>=<phase_start_iso> merged:<=<phase_end_iso>" --json number,title,mergedAt --limit 100
```

Sort by `mergedAt` ascending. Each PR earns one patch bump + one CHANGELOG entry.

### Step 8.2 — Patch-bump per PR

For each PR in order, sequentially:

a. **Bump patch:** `NEW_VERSION=$(npm version patch --no-git-tag-version | tr -d 'v')`.

b. **CHANGELOG entry.** If `CHANGELOG.md` doesn't exist, create with `# Changelog\n\n`. Read it first; if it doesn't start with the literal `# Changelog\n` header, STOP and surface (don't guess where to insert). Prepend after the header:
   ```
   ## [<NEW_VERSION>] - <YYYY-MM-DD>
   - PR #<N>: <title>
   ```

c. **Commit + tag (main only):**
   ```
   git add package.json CHANGELOG.md
   [ -f package-lock.json ] && git add package-lock.json
   git commit -m "Bump version to v<NEW_VERSION> (PR #<N>)"
   git tag "v<NEW_VERSION>"
   ```
   Tags land on the trunk at bump time. Promotion to `production` (if the project has it) carries the already-tagged commit — `/promote-production` does not tag.

### Step 8.3 — Minor-bump at phase close

After all PR patches:

a. `NEW_VERSION=$(npm version minor --no-git-tag-version | tr -d 'v')` — zeros the patch (e.g. 1.2.7 → 1.3.0).

b. CHANGELOG entry:
   ```
   ## [<NEW_VERSION>] - <YYYY-MM-DD> — Phase <N>
   - <points> pts shipped across <session count> sessions (throughput <pts/wk or burst>)
   - See `docs/RETROSPECTIVES.md` for the full retro
   ```

c. Commit + tag (main only):
   ```
   git add package.json CHANGELOG.md
   [ -f package-lock.json ] && git add package-lock.json
   git commit -m "Phase <N> close — bump to v<NEW_VERSION>"
   git tag "v<NEW_VERSION>"
   ```

### Step 8.4 — Push

```
git push origin "$WORKING_BRANCH"
```
If any tags were created in 8.2 or 8.3: `git push origin --tags`.

Echo: `Phase <N> closed at v<NEW_VERSION>` (and `tagged` if main).

## Step 9 — Offer next phase

"Phase <N+1> is next. Run `/start-phase <N+1>` now or stop here?" Let the user invoke `/start-phase` themselves — don't auto-chain.

## Step 10 — Summary

```
Phase <N> closed.
Points: <P> | Throughput: <pts/wk or burst> | Calibration: <K> re-est'd, <±D> drift
Span: <days>d | Sessions: <count> | PRs merged: <count>
Issues: <closed>/<created> closed; <moved> moved to Phase <N+1>
Retro: docs/RETROSPECTIVES.md
Version: v<NEW_VERSION>  (dev projects only; skipped if no package.json)
```

## Notes

- **Session files are read-only here.** Retro reads them; never writes. DEC-S013 atomicity.
- **No transcript is read anywhere.** DEC-S026 retired break inference and `active = wall − breaks` — the model whose `breaks = 0 → active = wall_clock` fallback was the bug that triggered the change.
- **GitHub IS the velocity data source now.** Step 2 reads issue `createdAt`/`closedAt` + `points:N` labels — that's the throughput input. `gh` is also used for issue accounting (Step 1), the points cross-check (Step 3), and version bumps (Step 8). If `gh` is down, Step 2 can't compute throughput; note it and let the user rerun. Don't guess.
- **The headline is throughput (points / calendar week), never reported without the calibration tally.** There is no `active`, `wall/pt`, `dev_time`, or `review_time` — all retired by DEC-S026. `wall_clock` survives only as the `/its-dead` on-screen gut-check.
- **Old retros carry retired columns.** Phases closed before DEC-S026 carry `Wall / Breaks / Active / h-pt` (or older `Dev / Review`) columns and an h/pt velocity — all retired, all on a different denominator. **Don't blend them with throughput.** History stays as written (DEC-S024 precedent); the standalone extractor `dev/claude/scripts/throughput.py` recomputes throughput straight from GitHub and is independent of any old retro prose.
