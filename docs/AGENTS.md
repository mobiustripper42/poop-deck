# [Project] — Claude Code Agents & Skills

## Overview
Several agents and slash-command skills support the development workflow. All run as Claude Code sessions, subagents, or slash commands. None are blocking — if one creates friction, drop it and revisit later. The summary table at the end of this doc is the canonical list — the per-skill sections below cover the original session-lifecycle set; newer skills (`/start-phase`, `/retro`, `/bump-major`, `/promote-production`, etc.) are documented in their own `SKILL.md` files under `.claude/skills/`.

---

## Agents

### 1. @architect

**Purpose:** Reviews architectural and design decisions before they're committed.

**When to invoke:**
- Before adding a new library or dependency
- When a task requires a pattern you haven't used yet
- When scope creep is knocking at the door
- When a task has a DEC-TBD flagged in PROJECT_PLAN.md

**Spec:** `.claude/agents/architect.md`

**Output:** Recommendation (proceed / modify / reject) with reasoning. Draft DECISIONS.md entry if proceeding.

---

### 2. @code-review

**Purpose:** Lightweight post-commit review. Catches issues, inconsistencies, and potential bugs.

**When to invoke:**
- After completing a task or set of related commits
- Before merging a phase
- Optional — skip if it's slowing you down

**Spec:** `.claude/agents/code-review.md`

**Output:** Findings list ranked by severity, or "Clean Bill of Health."

---

### 3. @pm

**Purpose:** Tracks project state. Knows what's done, what's next, what's blocked.

**When to invoke:**
- Start of every work session (via `/its-alive`)
- End of every work session (via `/its-dead`)
- Status checks ("where are we?")
- Scope cut decisions

**Spec:** `.claude/agents/pm.md`

**Output:** Updated `docs/PROJECT_PLAN.md`. Timeline risk flags. Scope cut recommendations.

---

### 4. @ui-reviewer

**Purpose:** Reviews visual design quality against the project's design system.

**When to invoke:**
- After completing a page or significant component
- At phase boundaries (formal review)
- When something "looks off" but you can't say why

**Spec:** `.claude/agents/ui-reviewer.md`

**Output:** Scored report (X/10) with prioritized issues and exact Tailwind class fixes.

---

### 5. @doc-consistency

**Purpose:** Cross-references factual claims across the project's doc set and flags mismatches and unfilled template placeholders. Report-only.

**When to invoke:** ad-hoc only — there is no scheduled or phase-boundary trigger. Reach for it when the docs *feel* like they've drifted apart, or after a session that churned several docs at once. It is not a ritual; don't run it on a calendar.
- Mid-project, anytime the docs feel like they've drifted apart
- After a session that touched multiple docs at once
- Via `/doc-consistency-check` (the only surface)

**Spec:** `.claude/agents/doc-consistency.md`

**Scope:** `docs/*.md` + root `CLAUDE.md`. Type-aware via `.claude/project-type` — `webapp` must declare brand in BRAND.md; `tool` must justify any "not used"; literal `PLACEHOLDER` is always a finding regardless of type.

**Hard fences:** no structural recommendations (DEC numbering, file ownership, "you should reorganize"), no edits, no copy editing. Fact-check only.

**Output:** Per-category pass/MISMATCH report with file:line refs and verbatim conflicting quotes. Zero-finding sweeps are a valid full report.

---

### 6. @tape-reader

**Purpose:** Audits session JSONL transcripts for workflow anti-patterns and proposes targeted improvements to skill and agent files.

**When to invoke:**
- Via `/read-the-tape`, after a session worth learning from

**Spec:** `.claude/agents/tape-reader.md`

**Output:** Anti-pattern findings (covers a known checklist; surfaces new candidate patterns) with proposed skill/agent edits.

---

### 7. @sync-config

**Purpose:** Classifies diffs between the project's live workflow files and the seeds template repo. Backports structural improvements (push) or forward-ports template changes (pull); flags cross-family patterns.

**When to invoke:**
- Via `/push-seeds` (project → seeds) or `/pull-seeds` (seeds → project)
- Also runs unattended via the nightly sync Routine

**Spec:** `.claude/agents/sync-config.md`

**Output:** Per-hunk classification (backport / forward-port / skip) and a proposed change set for review.

---

### 8. @ideas

**Purpose:** Idea curator. Captures new ideas as rows in `docs/FUTURE_IDEAS.md`, dedupes against what's already parked, cross-references SPEC/DECISIONS/PROJECT_PLAN/open issues, and keeps the prioritized index in sync.

**When to invoke:**
- To park a new idea without derailing the build
- To re-rank the index or audit the parking lot for staleness

**Spec:** `.claude/agents/ideas.md`

**Output:** A one-report curation summary (captured / dedup + cross-reference / flags). Edits only `docs/FUTURE_IDEAS.md`.

---

## Session Skills

Slash commands manage session lifecycle. Time tracking is automatic.

### /its-alive — Session Start

**Purpose:** Stamps start time, opens a per-session file, reads last session context, recommends next task.

**What it does:**
1. Ensures `.sessions-worktree/` exists (orphan `sessions` branch, DEC-S014)
2. Runs `date` to get current time
3. Opens a new per-session file `sessions/YYYY-MM-DD-HHMM-<dev>-<slug>.md` on the sessions branch, captures the active JSONL transcript path
4. Reads last completed session's Next Steps / In Progress / Blocked / Context
5. Reads PROJECT_PLAN.md for current phase and task state
6. Presents briefing with recommended task; waits for confirmation

**Spec:** `.claude/skills/its-alive/SKILL.md`

---

### /pause-this — Mid-Session Break

**Purpose:** Safe pause point within a session. Use when you need to walk away but aren't done with the task.

**What it does:**
1. Runs the build check from `CLAUDE.md §Commands` (skips if none defined)
2. Commits WIP with descriptive message
3. Notes pause point in the session file (but doesn't close it)

**Spec:** `.claude/skills/pause-this/SKILL.md`

---

### /restart-this — Resume from Pause

**Purpose:** Reload context after a mid-session break.

**What it does:**
1. Reads the pause note from the open session file
2. Reloads context from the session file and PROJECT_PLAN.md
3. No new session number, no new timestamp — resuming same session

**Spec:** `.claude/skills/restart-this/SKILL.md`

---

### /kill-this — Per-Task PR + Session-Log Update

**Purpose:** Ship one task. Build check, commit, push the task branch, run code review, open a PR, append a `## Task <N>` block to the session file. Runs **per task** (DEC-S013) — multiple times per Claude window.

**What it does:**
1. Runs the build check from `CLAUDE.md §Commands` (skips if none defined)
2. Commits code on the task branch with task prefix + Co-Authored-By, pushes
3. Runs @code-review against HEAD
4. Opens a PR (base = `main`) with `closes #<issue>`
5. Appends a `## Task <N>` block to the session file (on the orphan `sessions` branch). No time math, no version bump (those moved to `/retro`).

**Spec:** `.claude/skills/kill-this/SKILL.md`

---

### /its-dead — Session End (once per window)

**Purpose:** Close the session file. Run once at the end of a Claude window, after every task's `/kill-this` has shipped its PR.

**What it does:**
1. Stamps `ended:` and `status: closed` on the open session file
2. Tallies total points from the per-task blocks
3. Displays wall_clock to screen for a gut-check (no time math — that's `/retro`'s job)
4. Commits + pushes the sessions branch. The file is atomic after this.

**Spec:** `.claude/skills/its-dead/SKILL.md`

---

## Session Workflow

**Starting a work session:**
1. `/its-alive` → get briefing and task recommendation
2. Confirm what you're working on

**During a work session:**
3. Spec → Build → Test → Verify mobile screenshot
4. If hitting an architectural question → `@architect`
5. Ship each task with `/kill-this` (opens its own PR); if pausing → `/pause-this` → break → `/restart-this`

**Ending a work session:**
6. `/its-dead` once at the end of the window → close the session file, push
7. Merge PRs whenever convenient — order doesn't matter (DEC-S013)

**End of a phase:**
8. `@code-review` → review phase output
9. `@ui-reviewer` → design review (if UI-heavy phase)
10. `/retro` → close out the phase, write retro, version bumps (pgTAP, Playwright, external audits as the Phase Boundary Checklist demands)
11. Return to primary planning chat → review docs against intent

---

## Agent Summary

| Agent/Skill | Model | When | Purpose |
|-------------|-------|------|---------|
| @architect | Opus 4.8 | Before design decisions | Keep architecture coherent |
| @code-review | Sonnet | After commits, optional | Catch issues early |
| @pm | Sonnet | Start/end of sessions | Track progress, flag risks |
| @ui-reviewer | Sonnet | After UI work, phase boundaries | Design quality |
| @doc-consistency | Sonnet | Via `/doc-consistency-check`, ad-hoc when docs feel drifted | Cross-reference facts across docs; flag mismatches + placeholders. Report-only |
| @tape-reader | Sonnet | Via `/read-the-tape` | Audit JSONL transcripts for anti-patterns, propose skill improvements |
| @sync-config | Sonnet | Via `/push-seeds` / `/pull-seeds`, nightly Routine | Classify template diffs, propose backports/forward-ports |
| @ideas | Sonnet | Park an idea, re-rank, or audit the parking lot | Curate `docs/FUTURE_IDEAS.md`; edits only that file |
| /its-alive | — | Session start | Open session file + timestamp + briefing |
| /pause-this | — | Mid-session break | Safe pause with commit |
| /restart-this | — | Resume from pause | Reload context |
| /kill-this | — | Per task | Build check, commit, PR, append `## Task <N>` block |
| /its-dead | — | Session end (once per window) | Stamp `ended:`, tally points, close + push session file |
| /start-phase | — | Phase boundary (start) | Materialize phase as Issues |
| /retro | — | Phase boundary (end) | Close out phase, write retro, version bumps |
| /bump-major | — | Breaking change | Manual major version bump |
| /promote-production | — | Ship trunk to prod | ff-merge `main` → `production` (deploy-only), push |
| /doc-consistency-check | — | Ad-hoc, when docs feel drifted | Invokes @doc-consistency; cross-refs `docs/*.md` + root `CLAUDE.md` |
| /push-seeds | — | After workflow improvements | Backport project-side improvements to seeds templates |
| /pull-seeds | — | After seeds gets new improvements | Pull template changes into this project |
| /read-the-tape | — | After a session worth learning from | Audit session JSONL for anti-patterns |

**Per-session files:** the workflow uses `sessions/YYYY-MM-DD-HHMM-<dev>-<slug>.md` (one file per session) on the orphan `sessions` branch via `.sessions-worktree/` (DEC-S014). `<dev>` comes from `~/.claude/devname` (one-line file, falls back to `$USER`). The slug is derived from the branch name (`task/X-foo` → `X-foo`, `main` → `main`, etc.). The active JSONL transcript path is captured in the file's frontmatter for later `/read-the-tape` audits.

**Task model (post phase-rituals rollout):** `PROJECT_PLAN.md` is a phase-boundary document — read at planning, written at retro. Current-phase tasks materialize as GitHub Issues with `phase:N` + `points:X` labels. The plan stays untouched mid-phase, eliminating merge contention with multiple devs.
