---
name: pull-seeds
description: Pulls seeds template improvements into the active project. Resolves the seeds checkout, gates on schema version compatibility, then invokes @sync-config in pull direction to classify diffs and apply approved changes to the project's live files. Counterpart to /push-seeds.
tools: Read, Edit, Write, Bash, Glob, Grep, Agent
---

You are executing the /pull-seeds skill. The user wants to pull seeds template improvements into this project.

## Step 0 — Resolve the seeds checkout

The seeds repo lives outside this project. Find it in this order; stop at the first hit:

1. **Skill arg:** if invoked as `/pull-seeds <path>`, use that path as `SEEDS`.
2. **Sibling default:** `SEEDS=$(git rev-parse --show-toplevel)/../seeds` if a git repo exists at that path (`git -C "$SEEDS" rev-parse --git-dir 2>/dev/null`).
3. **Env var:** `$SEEDS_REPO` if set and a git repo exists at that path.
4. **STOP:** if none resolve, ask: "Where's your seeds checkout? Re-run as `/pull-seeds /path/to/seeds`."

Echo: "Seeds checkout: `$SEEDS`."

## Step 0.5 — Seeds checkout freshness

`seeds-version` and template files are read straight off disk in later steps. Stale or feature-branch checkouts produce wrong syncs — refresh first. The seeds checkout is the contract; never let it drift silently.

**Branch check:**
```
SEEDS_BRANCH=$(git -C "$SEEDS" branch --show-current)
```
If `SEEDS_BRANCH != main`: STOP. "Seeds checkout is on `$SEEDS_BRANCH`, not `main`. Pulling templates from a feature branch usually means the wrong files. Switch (`git -C $SEEDS checkout main`) and re-run, or pass an explicit path if you really mean to pull from a feature branch."

**Fetch + distance check:**
```
git -C "$SEEDS" fetch origin main
BEHIND=$(git -C "$SEEDS" rev-list --count main..origin/main)
AHEAD=$(git -C "$SEEDS" rev-list --count origin/main..main)
```
- **`BEHIND=0` and `AHEAD=0`:** echo "Seeds checkout up-to-date with origin/main." Continue.
- **`BEHIND>0` and `AHEAD=0`:** ASK "Seeds is behind origin/main by $BEHIND commit(s). Pull now? (y/n)" Wait. If yes: `git -C "$SEEDS" pull --ff-only origin main`. If no: STOP — pulling templates from a stale seeds checkout is the wrong move.
- **`AHEAD>0`:** STOP. "Seeds local main has $AHEAD un-pushed commit(s) (may also be behind). Never auto-resolve seeds-side state. Inspect: `git -C $SEEDS log --oneline origin/main..main` and `git -C $SEEDS log --oneline main..origin/main`."

**Verify the version file is now present:**
```
[ -f "$SEEDS/seeds-version" ]
```
If still not: STOP. "`$SEEDS/seeds-version` doesn't exist even after refresh. The file lives at the seeds repo root from V2 onward. Either this is a pre-V2 seeds checkout (extremely unlikely if you're running /pull-seeds) or the file was deleted — investigate before continuing."

## Step 1 — Schema version compatibility check (gating)

Read both versions:

```
SEEDS_VER=$(cat "$SEEDS/seeds-version")
PROJECT_VER=$(cat .claude/seeds-version 2>/dev/null)
```

If `.claude/seeds-version` does not exist: STOP. "This project has no `.claude/seeds-version`. It's either pre-V2 (run the migration first — see `$SEEDS/docs/SCHEMA_VERSIONS.md` § Migration notes) or has never been seeded. If you know the version, set it explicitly: `mkdir -p .claude && echo N > .claude/seeds-version`."

Compare:

- **`PROJECT_VER == SEEDS_VER`:** echo "Schema versions match (v$SEEDS_VER). Proceeding." Continue to Step 2.
- **`PROJECT_VER < SEEDS_VER`:** STOP. "Project is on v$PROJECT_VER, seeds is on v$SEEDS_VER. Pull would install incompatible templates. Run the v$PROJECT_VER → v$SEEDS_VER migration first — see `$SEEDS/docs/SCHEMA_VERSIONS.md` § Migration notes."
- **`PROJECT_VER > SEEDS_VER`:** STOP. "Project is ahead of seeds (v$PROJECT_VER vs v$SEEDS_VER). Did you mean `/push-seeds`?"

Never auto-migrate. Migrations touch session files and `PROJECT_PLAN.md` — blast radius is too high for silent runs.

## Step 2 — Working tree check

Refuse to apply changes onto a dirty tree — mixing template-pull and WIP commits is unreviewable.

```
git status --porcelain
```

If non-empty: STOP. "Working tree is dirty. Commit or stash WIP first, then re-run `/pull-seeds`."

## Step 3 — Branch check

`/pull-seeds` should land its changes in a single reviewable PR. Confirm or cut a fresh branch.

`BRANCH=$(git branch --show-current)`.

- **`BRANCH=main`:** ask "Cut a fresh branch for this pull? Suggested: `task/pull-seeds-$(date +%Y-%m-%d)`. (y/n)" Wait. If yes: `git checkout -b task/pull-seeds-$(date +%Y-%m-%d)`. If no: confirm "Apply directly on `main`? Pull-seeds changes will mix with whatever lands next. (y/n)" — proceed only on explicit yes.
- **`BRANCH` matches `task/pull-seeds-*` or `task/seeds-sync-*`:** good — proceed.
- **Other branch:** warn "You're on `$BRANCH`. Pulling seeds changes here mixes them with that work. (a) continue here, (b) switch to main and cut a fresh branch, (c) abort?" Wait.

## Step 4 — Invoke @sync-config in pull direction

Hand off to the @sync-config agent with an explicit direction parameter and the seeds path:

> Run in PULL direction. Source: `$SEEDS`. Target: this project's working tree (run from `$(git rev-parse --show-toplevel)`).
>
> Diff each file pair per your Step 1 rubric (project file vs seeds template). Classify hunks per your Step 2 rubric. For each "structural improvement" present in the template but not in the project, show the diff and ask "Apply to project? (y/n)". For project-side customizations not present in the template, leave the project file alone — those are the project's own concretions, not template drift.
>
> When applying, follow your Step 4 PULL rules: preserve project-specific substitutions ([Project] → existing concrete name, generic deadlines → existing concrete dates, etc.).
>
> Report which files changed, which were skipped, and any cross-family patterns flagged.

Wait for the agent to finish.

## Step 5 — Surface results + commit hand-off

The agent has applied approved changes to project files. Show the user:

- **Files changed** — paths under `.claude/` and `docs/`
- **Skipped** — what the agent classified as project-specific and left alone
- **Flagged** — any cross-family `shared/` candidates surfaced

Then:

> Review the diff (`git diff`). When you're satisfied, run `/kill-this` to commit + open a PR. Don't bump `.claude/seeds-version` unless you're catching up across schema versions — pull within the same version doesn't change it.

Do **not** commit automatically. Pulled changes touch skill bodies and docs that materially affect future sessions; the human reads them before they land.
