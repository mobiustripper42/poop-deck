---
name: its-alive
description: Session start. Stamps the start time, opens a per-session file on the orphan `sessions` branch via `.sessions-worktree/`, captures the active JSONL transcript path, reads last session context, reads the project plan, and presents a briefing with task recommendation. Waits for confirmation before any work begins.
tools: Read, Edit, Write, Bash, Glob, Grep, Agent
---

You are executing the session start ritual.

## Step 0 — Branch check

**Worktree check first:** run `git rev-parse --git-dir`.
- If the output contains `/worktrees/`: this is a **linked worktree session** (concurrent with another session). Skip the rest of Step 0 — the branch here is intentional. Note "Linked worktree" in the briefing output and continue to Step 0.6.
- Otherwise: continue.

Run `git fetch origin` to refresh remote state. Capture `BRANCH=$(git branch --show-current)`.

**Branch handling:**
- `task/*` or other intentional feature branch: continue (PR-flow project).
- `claude/*` (CC Desktop / web / mobile auto-branch): accept and continue. The platform pre-cuts this branch when launching a session. Per DEC-S013, this branch is the **session-anchor**; per-task code branches get cut as work proceeds, each PR'd separately. Session-file commits go to the orphan `sessions` branch via the worktree (DEC-S014), NOT to this branch.
- `main`: `git pull --ff-only origin main`. On divergence, show `git log --oneline origin/main..HEAD` and `git log --oneline HEAD..origin/main`, then ask: **"(a) rebase, (b) reset to origin/main, (c) abort?"** Wait for the choice.
- Anything else (manual non-standard branch): if `git status --porcelain` is dirty, stop and ask the user to commit/stash. If clean, ask the user **"Stay on `$BRANCH` or switch to `main`?"** Wait for the choice.

### Step 0.5 — Orphan branch + PR-state scan

Before stamping time, check for leftover work from prior sessions. The CC platform creates a new `claude/*` branch per session, so previous sessions' branches and PRs stay alive on the remote until explicitly merged or deleted. After a **squash merge** (GitHub's default for this workflow), the branch's original commits never appear on `$WORKING_BRANCH` — which has only the squashed commit — so a naive "commits not on main" scan flags every shipped branch as an orphan. Step 0.5 must cross-reference PR state to avoid that false alarm.

**Resolve `WORKING_BRANCH`:**
```
WORKING_BRANCH=main
```
The active trunk is always `main` (DEC-S022); a `production` branch, if present, is a downstream deploy pointer and never the orphan-scan base.

**Scan A — remote `claude/*` branches with commits not on `$WORKING_BRANCH`:**
```
git for-each-ref refs/remotes/origin/claude/ --format='%(refname:short)'
```
For each `origin/claude/<slug>` (other than the current branch): `git log --oneline origin/$WORKING_BRANCH..<ref>`. If non-empty, it's a Scan-A candidate.

**Scan B — PRs (open AND closed) keyed by branch:**
- `gh pr list --state all --base "$WORKING_BRANCH" --json number,title,headRefName,state,mergedAt,createdAt,updatedAt --limit 50` (or `mcp__github__list_pull_requests` with `state: all` if `gh` is unavailable).

For each Scan-A candidate, find the most recent PR whose `headRefName` matches the branch's short name (strip the `origin/` prefix; highest PR number wins). The PR's state and merge status determine the category:

| Category | Definition | Action |
|----------|------------|--------|
| Open-with-PR | Most recent PR is OPEN | Silent. In-flight — nothing to do. |
| Merged-cleanable | Most recent PR is CLOSED with `mergedAt` set (non-null) | Silent. Squash-merge artifact, safe to delete but harmless. Don't prompt. |
| Orphan-abandoned | Most recent PR is CLOSED with `mergedAt` null | Silent. PR closed without merging — the close was the decision. |
| Orphan-without-PR | Branch has commits but NO PR was ever opened for it | **Real problem — work has no shipping path.** Surface and **wait**: "(a) open a PR now, (b) cherry-pick onto current branch, (c) delete (commits lost)?" |
| Stale-no-commits | Branch on remote, zero commits ahead of `$WORKING_BRANCH` and no associated PR commits | Silent. |

**Why the PR cross-reference still runs even though only one category surfaces.** Scan B is not optional decoration — it's what keeps **Orphan-without-PR** honest. Without the merged-state lookup, every squash-merged branch (whose original commits never land on `$WORKING_BRANCH`) would match "branch has commits, looks like no PR" and false-alarm every session. The cross-reference is what tells a genuinely-orphaned branch apart from a shipped-and-squashed one. Keep the scan; suppress the output.

**Gating rule.** Surface **exactly one** category: **Orphan-without-PR**, and only when it's non-empty — that's real lost work with no shipping path, and it blocks the briefing until the user decides. Every other category is computed silently and produces **no output and no prompt**. The old per-session nag (merged-branch cleanup prompts, abandoned-PR advisories, stale-branch deletion suggestions) is gone — it printed "nothing wrong" every session and trained you to ignore it. If you ever want to reap merged/stale branches, that's an explicit ad-hoc ask, not a session-open ritual.

**Tool-outage fallback.** If `gh` and `mcp__github__list_pull_requests` are both unavailable, skip Scan B entirely and surface every Scan-A candidate as "branch has commits — PR state check unavailable, do not assume orphan." Don't false-alarm during a tool outage. Note the skipped check in the session Context section.

### Step 0.6 — Ensure `.sessions-worktree/` (DEC-S014)

The session file lives on an orphan `sessions` branch checked out at `.sessions-worktree/`. Skills commit there; the user's main checkout never moves.

**Check for worktree.** `[ -d .sessions-worktree/.git ] && echo present || echo missing`.

**If present:** `cd .sessions-worktree && git fetch origin sessions && git reset --hard origin/sessions && cd ..`. Continue to Step 1.

**If missing — three sub-cases:**

a. **`origin/sessions` exists on remote** (fresh clone / accidental delete): `git worktree add .sessions-worktree sessions origin/sessions`. Continue.

b. **`origin/sessions` does NOT exist** (first run on this project — migration path): bootstrap the orphan branch.
```
git checkout --orphan sessions
git rm -rf . 2>/dev/null || true
# If a sessions/ dir existed on main, bring its contents over:
git checkout main -- sessions/ 2>/dev/null || mkdir -p sessions
[ -d sessions ] || mkdir sessions
[ -f sessions/README.md ] || echo "# Sessions branch (DEC-S014). Each project session writes one file here." > sessions/README.md
git add sessions/
git commit -m "Initialize sessions branch"
git push -u origin sessions
git checkout main
# Remove sessions/ from main if it existed:
[ -d sessions ] && git rm -r sessions && git commit -m "Move sessions to orphan sessions branch (DEC-S014)" && git push origin main
# Add .gitignore entry on main:
grep -q "^\.sessions-worktree/" .gitignore 2>/dev/null || (echo ".sessions-worktree/" >> .gitignore && git add .gitignore && git commit -m "Ignore .sessions-worktree (DEC-S014)" && git push origin main)
# Attach worktree:
git worktree add .sessions-worktree sessions
```
Note: on protected main, the two follow-up commits (remove `sessions/`, add `.gitignore`) may need a PR instead of direct push. Detect with `gh api repos/{owner}/{repo}/branches/main/protection --silent 2>/dev/null`; if protected, open a "Migrate to DEC-S014" PR with those commits on a `claude/dec-014-migrate` branch and surface the URL.

c. **`origin/sessions` exists but local sessions/ also has uncommitted files** (mid-migration): stop and ask the user to resolve manually.

After Step 0.6 completes, `.sessions-worktree/` is checked out to the `sessions` branch and reflects `origin/sessions`. All subsequent session-file paths in this skill refer to `.sessions-worktree/sessions/<file>.md`.

## Step 1 — Stamp the time

```
START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
DATE_PART=$(date -u +%Y-%m-%d)
TIME_PART=$(date -u +%H%M)
```

## Step 2 — Resolve dev identity

Use the **Read** tool on `~/.claude/devname`. If it succeeds, `DEV` = the trimmed file contents. Done.

If Read errors (file does not exist), prompt the user once for their dev handle and offer to write `~/.claude/devname` via the **Write** tool. Once written, `DEV` = the handle. Done.

**Do NOT fall back to `echo "$USER"` or any other Bash-based identity probe.** The `$USER` branch was removed because: (a) the harness validator flags `$USER`-shaped Bash commands on a rolling cadence as new patterns land — so every fix to the validator-silence wording was only good until the next validator pattern landed; (b) `$USER` is unreliable in sandboxed environments where `~/.claude/devname` doesn't persist between sessions anyway, so the fallback was solving the wrong problem; (c) the prompt + Write path resolves to a real persistent value that future sessions read directly. The Read + Write path is the only path. If Read fails, the prompt is mandatory.

## Step 3 — Derive the slug

```
case "$BRANCH" in
  task/*)    SLUG="${BRANCH#task/}" ;;
  feature/*) SLUG="${BRANCH#feature/}" ;;
  claude/*)  SLUG="${BRANCH#claude/}" ;;
  main|master) SLUG="main" ;;
  *) SLUG=$(echo "$BRANCH" | tr '/' '-') ;;
esac
```

Sanitize: lowercase, replace any non-`[a-z0-9.-]` with `-`, collapse repeats.

**Concurrent session check** (now reads from the worktree, not main): `grep -l "^status: open" .sessions-worktree/sessions/*.md 2>/dev/null`. If a session is already open, ask:
- **(a) concurrent** → set up a linked git worktree for the new task as before (separate from `.sessions-worktree/`, which is for the sessions branch — the linked worktree is for the new task's code branch).
- **(b) stale** → mark `status: abandoned` in the open file and continue.

## Step 4 — Determine session number

Use the **Glob** tool with `path: .sessions-worktree/sessions` and `pattern: *.md` to list current session files. Filter out `README.md` from the result. Call the remaining count `NEW_COUNT`.

Use the **Grep** tool on `session-log.md` (legacy archive on `main`) with `pattern: "^## Session [0-9]+"` and `output_mode: content`. If matches come back, parse the integer from each line and take the maximum — call it `LEGACY_MAX`. If `session-log.md` is absent or returns no matches, `LEGACY_MAX = 0`.

`SESSION_NUM = LEGACY_MAX + NEW_COUNT + 1`. Compute in head — no bash needed.

(Glob + Grep replaces a chained `ls | wc -l` + `grep | grep | sort | tail` pipeline — same validator-silence reason as Step 5.)

## Step 5 — Capture the transcript path

```
echo "$HOME/.claude/projects/$(pwd | tr '/' '-')"
```

Capture as `JSONL_DIR`. Use the **Glob** tool with `path: <JSONL_DIR>` and `pattern: *.jsonl`. `TRANSCRIPT = result[0]`. If empty, leave `transcript:` blank.

## Step 6 — Write the open session file (in the worktree)

```
SESSION_FILE=".sessions-worktree/sessions/${DATE_PART}-${TIME_PART}-${DEV}-${SLUG}.md"
```

Write the file with this content (DEC-S013 schema — atomic, no time math fields):

```
---
session: <N>
dev: <DEV>
slug: <SLUG>
branch: <BRANCH>
started: <START_UTC>
ended:
points:
pr_numbers: []
status: open
transcript: <TRANSCRIPT>
---

# Session <N> — <SLUG>

<!-- Task blocks appended by /kill-this, one per task. -->

**Next Steps:**

**Context:**
```

Commit and push **on the sessions branch** using `git -C` to target the worktree directory (no `cd` — shell state doesn't persist between Bash tool calls):

```
git -C .sessions-worktree add sessions/$(basename "$SESSION_FILE")
git -C .sessions-worktree commit -m "Open Session $SESSION_NUM entry"
git -C .sessions-worktree push origin sessions
git -C .sessions-worktree checkout sessions 2>/dev/null || true
```

The final `checkout sessions` re-pins the worktree HEAD to the `sessions` branch — guards against a detached-HEAD state.

## Step 7 — Read last session context

Find the most recent CLOSED session file in the worktree:

```
PREV=$(ls -t .sessions-worktree/sessions/*.md 2>/dev/null | grep -v README | grep -v "$(basename $SESSION_FILE)" | head -10)
```

For each candidate (newest first), check for `status: closed`. The first match is the previous session. If none exist, fall back to the top entry of `session-log.md` (legacy archive) if present.

Extract:
- **Task blocks** (`## Task <N>` sections in the body) — what was shipped
- **Next Steps** — verbatim
- **Context** — gotchas

**Pre-DEC-S013 schema tolerance:** legacy session files use a single `Task:` block instead of `## Task <N>` headers. Read either shape.

## Step 8 — Read project state

**Skip-when-directed.** If the user already named a task or goal when they launched this session, you do **not** need to compute a recommendation — they've told you what they're doing. Skip the recommendation-building below; Step 7's context read (last session, Next Steps, gotchas) is the part that always matters. The recommendation exists for the cold open, when you start a session with no task in hand. Don't spend the session's first move ranking the backlog the user has already overruled.

When a recommendation *is* wanted (cold open), grep `docs/PROJECT_PLAN.md`:
- Unchecked: `grep "\[ \]" docs/PROJECT_PLAN.md`
- Deferred: `grep "\[~\]" docs/PROJECT_PLAN.md`
- Priority: `grep "Next session priority" docs/PROJECT_PLAN.md -A 2`
- Current phase: `grep -E "^## Phase " docs/PROJECT_PLAN.md | head -3`
- Velocity: `grep "Velocity baseline" docs/PROJECT_PLAN.md -A 1`

If the project uses phase-rituals: `gh issue list --label "phase:current" --state open --json number,title,labels --limit 50`.

## Step 9 — Present briefing

```
Session <N> — <DATE_PART>
Started: <local time> (<UTC time>)
Branch (session anchor): <BRANCH>
Session file: <SESSION_FILE>   (lives on `sessions` branch via .sessions-worktree/)
Dev: <DEV>

Last session: [one-line summary]

Next Steps from last session: [verbatim or paraphrased]
Context to remember: [gotchas worth mentioning]

Recommended task: [task ID + name + why — OMIT this line entirely if the user opened with their own task]

Branch already cut: <BRANCH> — good to go. Each task today gets its own /kill-this; the session file lives on the orphan `sessions` branch independent of any task branch.
```

Then ask: **"Ready to go? Confirm the task or redirect me."** — or, if the user already named the task, just confirm you've got the context and restate their task in one line: **"Context loaded. Picking up <their task> — go?"**

Stop. Do not begin work until the user confirms.

## DEC-S013 + DEC-S014 reminders

- One Claude window opens **one** session. `/its-dead` runs **once** at the end.
- `/kill-this` may run multiple times — one per task — each opens its own PR and appends a `## Task <N>` block to this session file (on the sessions branch).
- Time math happens at `/retro`, not at close. `/its-dead` displays wall_clock to screen for gut-check but writes no time field.
- Once `/its-dead` writes `ended:` and `status: closed`, this file is never modified again. Atomic.
