# Velocity Tracking & Scrum Poker — How-To Guide

A lightweight solo-dev process for tracking effort, estimating work, and knowing where you stand against a deadline. Built for CC-assisted development with fragmented time.

---

## Part 1: Velocity Tracking

> **The quick version** — how to *read* the numbers, with worked examples — lives in [`THROUGHPUT_QUICKREF.md`](THROUGHPUT_QUICKREF.md). This part is the *why*. The full decision record is DEC-S026 in `DECISIONS.md`.

### What it measures

**Velocity = throughput: effort points shipped per calendar week.** Higher is faster. It's read straight from GitHub — issue `closedAt` dates + `points:N` labels — so it measures the rate at which work *clears the board*, not hours at the keyboard.

Two lifetime rates come out of it:
- **points / calendar-week** — realized pace, *including* idle weeks. This is your honest clearance rate.
- **points / active-week** — intensity in the weeks you actually shipped something.

This is the metric *after* three failed attempts (DEC-S013 → S015 → S024) to measure "active hours per point" by reconstructing keyboard time from the session transcript. That metric is **retired** — the transcript lives on an unreachable path for nearly every web/Desktop session, so the number rotted by default. For a solo + Claude shop the insight was that effort-hours aren't even the scarce quantity: Claude does the labor, so what you actually care about is *calendar clearance rate* and *estimate stability*. Both are measurable from GitHub forever. (Full autopsy: DEC-S026.)

### Where it comes from — you don't log anything

There is no tracker to maintain and no "log your hours" step — same promise as before, now actually kept, because the inputs are data GitHub holds whether you think about it or not:

- Every task is a GitHub Issue with a `points:N` label (added by `/start-phase`) and a `closedAt` date (stamped when its PR merges). That's the entire dataset.
- `/retro` does the math at phase close: it groups closed issues by phase, sums points, and divides by the calendar span — no session file, no transcript, no `started`/`ended` arithmetic.
- The **source of truth is GitHub itself.** RETROSPECTIVES.md and the PROJECT_PLAN.md table are now *mirrors* of a number that's always recomputable from issue dates + labels — they can't drift the headline, because the headline isn't stored in them.

The one thing that makes a project invisible: no `points:N` labels. Throughput reaches back exactly as far as the labelling ritual and no further — a project from before you labelled issues returns nothing (same blind spot the old metric had).

### Your overall number, and across projects

For your lifetime number — or a combined number across several repos — run the **throughput extractor** (`dev/claude/scripts/throughput.py`), pointing it at one or more project paths:

```bash
python3 dev/claude/scripts/throughput.py ~/bushel
python3 dev/claude/scripts/throughput.py ~/bushel ~/muster ~/helm   # cross-repo rollup
python3 dev/claude/scripts/throughput.py --issues ~/bushel          # + points histogram
```

It reads GitHub directly (needs `gh` installed and authed): points off closed issues, dates off the issues and merged PRs. It prints the two lifetime rates, a per-phase breakdown with pointing-stability and span, and PR merge latency. A project with no `points:N`-labelled closed issues prints "nothing to measure" — not an error, just a project that predates the ritual.

### Reading the numbers

- **Throughput is an active-time rate, not a calendar date.** A slow week and a vacation week look identical to it. To forecast "when does it ship," divide remaining points by *your* real availability — the tool measures the work, you supply the calendar. Never quote it as at-keyboard speed.
- **Pointing stability (`pts/issue`) is the estimate-calibration signal.** The per-phase breakdown prints a `tight` / `drifting` verdict on how consistent your `pts/issue` is. Tight = your estimates hold their value over time; drifting = scope is growing or points are inflating. This is the number to watch, and the one the old metric was secretly also trying to measure.
- **Per-phase `pts/wk` only appears for phases spanning ≥7 days.** A phase you closed in an afternoon has no meaningful weekly rate — it's recorded as `burst — N pts over Dd` instead. Dividing points by a sub-week denominator produces nonsense (one project showed 516 pts/wk off a single 1-pointer).
- **PR merge latency is flow-health, NOT effort.** The extractor reports median + p85 hours from PR-open to merge. That answers "do my PRs sit unmerged?" — it does **not** scale with task size (the PR opens *after* the build is done, so it can't see build time; it comes back flat across 2/3/5-pointers by design). Read it as "is the pipe clogged," nothing more.
- **Throughput is even more project-shape-specific than the old metric.** Never forecast a new project from another's throughput — project shapes differ too much. The number describes the project you ran it on, full stop. (Historical phases closed under the retired model keep their old columns; `throughput.py` recomputes from GitHub independently, so history needs no backfill.)

### Rules of thumb

- **It only works if your pointing is consistent.** Throughput converts your estimate into a clearance rate; if you point the same task a 3 on Tuesday and an 8 on Friday, the rate measures estimation noise, not speed. Consistent-but-biased pointing is fine — the bias is in both the history and the forecast, so it cancels. Random pointing is not. The `pts/issue` stability verdict is the test: tight = your pointing holds; drifting = it doesn't.
- **It's coarse — treat it as ±50%.** Solo work is bursty (every project in the fleet has been a 1–6 week sprint, then done). Read the headline as a band ("ships in ~5–8 weeks"), never a precise date.
- **Don't fudge.** The point is accurate forecasting, not looking fast.
- **Re-estimate when surprised** — if a 3 turns into an 8, update the plan. That's data, not failure.

---

## Part 2: Scrum Poker (Estimation)

### The scale

**Fibonacci sequence: 2, 3, 5, 8, 13**

| Points | Meaning | Examples |
|--------|---------|----------|
| **2** | Small, well-understood, minimal unknowns | Add a column to a table, wire up an existing API endpoint, simple UI component |
| **3** | Moderate, clear approach, maybe one unknown | CRUD page with form validation, API client with auth + error handling |
| **5** | Significant work, some complexity or unknowns | Agent prompt design + structured output, data normalization pipeline, schedule board UI |
| **8** | Large, multiple moving parts, real unknowns | Full admin view with multiple interactive components, complex agent with business rules |
| **13** | Epic — probably should be broken up | Full auth system, complete write-back pipeline with error recovery. If you see a 13, ask: can this be two 5s and a 3? |

**No 1s** — if it's that small, just do it. Don't plan it.
**No 13s if avoidable** — break them down. A 13 means you don't understand the task well enough yet.

**Points size estimation, not execution units.** A point is a relative planning number calibrated to your own velocity — *not* a ceiling on how much Claude builds in one run. Current models hold coherence across far more than an 8, and splitting a *coherent* task to honor a points ceiling fragments context and can lower quality (two stitched 5s < one well-specified 8). Split execution units by **reviewability, blast radius, reversibility, and migration conflicts** — not by "the model can't hold it." A coherent 8 is a fine single unit; a genuine 13 still gets broken up (you don't understand it well enough yet, and the diff is hard to review). See CLAUDE.md § Scope Discipline.

### How to poker (solo dev + Claude)

**Setup:** Claude proposes effort for each task in a phase. You review.

**The conversation:**
```
Claude: "Task 2.4 — Shift editing (split/merge/delete). I say 5."
You: "That's an 8. The merge logic has edge cases with gaps."
Claude: "Fair. What makes it an 8 vs a 5?"
You: "Merging two shifts means re-linking all the Xola event IDs 
      and recalculating crew requirements. It's not just UI."
Claude: "Agreed — 8. I'll note the merge complexity in the task description."
```

**Rules:**
1. **Disagree openly.** The whole point is catching misestimates before you're mid-build.
2. **Justify the gap.** If you say 8 and Claude says 3, one of you is missing something. Talk it out.
3. **The person doing the work wins ties.** You know your codebase and your constraints better than Claude does.
4. **Record disagreements.** PROJECT_PLAN.md has an "Estimation Poker — Standing Disagreements" table. If you can't resolve it, log it and revisit when you start the task.
5. **Re-estimate when surprised.** If a 3 turns into an 8 mid-session, update the plan. That's data, not failure.

### When to re-estimate

- **Before starting a new phase** — review all tasks, re-score anything that looks different now that you know more
- **After a task takes 2x+ the expected hours** — either the estimate was wrong or the task changed. Update the plan.
- **When cutting scope** — removed tasks get zeroed out, deferred tasks get marked, remaining estimates may shift

### Anti-patterns

- **Anchoring:** Don't let the first number stick without challenge. If Claude says 3 and you instinctively agree, pause and think about what could go wrong.
- **Sandbagging:** Don't inflate estimates to build in buffer. The velocity tracker already accounts for your actual pace — padding estimates just makes the projections useless.
- **Precision theater:** Don't debate whether something is a 4 or a 5. Pick the nearest Fibonacci number and move on. The scale is intentionally coarse.
- **Estimating during the build:** If you're mid-task and realize it's bigger, stop estimating and just finish it. Log the actual hours. Re-estimate the *next* similar task.

---

## Part 3: Putting It Together

### Rhythm

**Per phase start:** run `/start-phase`. It turns the phase's tasks into GitHub Issues with `points:N` labels — which *is* the throughput dataset. No labels, no velocity, so this is the step that matters.

**Per phase boundary:** run `/retro`. It computes the phase throughput + the pointing-stability tally off GitHub issue dates and labels, writes RETROSPECTIVES.md, and updates the PROJECT_PLAN.md velocity table. If you're starting a new phase, do estimation poker (Part 2) on its tasks.

**When you want the big picture:** run the throughput extractor (Part 1) for your lifetime or cross-repo number. Check remaining points against *your* available calendar time — throughput is a clearance rate, not a date, so you supply the availability. If the work won't fit before a deadline, cut scope (PROJECT_PLAN.md has a cuttable-tasks list).

### Cross-project tracking

Each project's throughput is read from its own GitHub issues. Throughput is per-project and per-shape — don't average a CRUD app against an agent pipeline. When you want a combined view, the extractor takes multiple repo paths and reports each repo plus the rollup.

### The one thing that matters

**Point consistently and label every issue.** Everything downstream — the per-phase throughput, the forecasts, the cross-repo rollup — is recomputed from GitHub issue dates + `points:N` labels, so there's nothing to log and nothing to forget. The only input that can quietly poison the number is inconsistent pointing, because throughput can't tell "I got slower" from "I pointed it lower." Keep your pointing honest and the system does the rest.
