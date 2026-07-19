# [Project Name] — Claude Code Project Context

> **Read `.claude/CLAUDE-context.md` first.** It holds this project's name, stack, data model, commands, and any project-specific overrides to the workflow and conventions below. Treat it as authoritative for every project-specific fact. If the file does not exist, stop and tell the user to create it from the seeds template (`dev/claude/CLAUDE-context.md`) before continuing.
>
> This `CLAUDE.md` is a **seeds-managed shell** (DEC-S019): it carries only project-agnostic workflow guidance and syncs from seeds untouched. Do **not** add project-specific content here — it belongs in `.claude/CLAUDE-context.md`, or the next sync will overwrite it.

## Key Docs
| File | Purpose |
|------|-------|
| `docs/SPEC.md` | What we're building — scope, V1 vs V2 vs V3 |
| `docs/DECISIONS.md` | Why we made each architectural choice |
| `docs/USER_STORIES.md` | What each role does |
| `docs/PROJECT_PLAN.md` | Phases, scope, velocity. **Phase-boundary doc** — read at planning, written at retro. Current-phase tasks live in GitHub Issues. |
| `docs/RETROSPECTIVES.md` | Phase-end retrospectives — written by `/retro` |
| `docs/AGENTS.md` | Agent and skill specs (canonical). |
| `docs/BRAND.md` | Voice, visual direction, philosophy |
| `docs/VELOCITY_AND_POKER_GUIDE.md` | Estimation methodology |
| `docs/CHEATSHEET.md` | One-page printable skill reference |
| `sessions/*.md` (on orphan `sessions` branch via `.sessions-worktree/`) | Per-session files — `YYYY-MM-DD-HHMM-<dev>-<slug>.md`. Atomic after `/its-dead` closes (DEC-S013); orphan branch decouples session log from any code branch (DEC-S014). |
| `.claude/seeds-version` | Schema version this project was last installed at. Used by `/pull-seeds` to gate template syncs. |
| `.claude/project-type` | Project type — `webapp` or `tool`. Used by `@sync-config` to gate template files that don't apply to this project's type (DEC-S011). Optional. |

Project-specific docs are listed in `.claude/CLAUDE-context.md` under `## Additional Docs`.

## Micro Workflow (every task, no exceptions)

1. **Spec it** — poker estimate, acceptance criteria. Issue exists from `/start-phase`.
2. **Plan it** — summarize what you're going to do. Wait for explicit approval before writing code or running commands.
3. **Cut the branch** — once approved: `git checkout -b task/X.Y-short-description`.
4. **Build it**
5. **Write the test** — Playwright integration test + pgTAP if RLS-touching. Test-first when behavior is changing.
6. **Run targeted tests** — `npx playwright test tests/foo.spec.ts --project=desktop`. `supabase test db` if RLS-touching. Do NOT run full suite — that's the user's call.
7. **Mobile screenshot** — confirm 375px viewport passes
8. **Ship the task** — `/kill-this` commits, pushes, opens PR with `closes #<issue>`, appends a `## Task <N>` block to the session file (on the orphan `sessions` branch). Run per task; multiple per session.
9. **Pick up another task or close out** — start step 1 with a new branch, or run `/its-dead` once at the end of the Claude window. Merge PRs whenever — order doesn't matter.

**No test, no push.**

**Full suite (`npx playwright test`) is never run automatically.** Ask first.

Project-specific step overrides (e.g. a tool project with no database swaps the test steps) live in `.claude/CLAUDE-context.md` under `## Workflow Overrides`.

## Migration Protocol

- **All schema changes go through migrations.** No exceptions. Migrations are the source of truth — never edit schema through a dashboard on any environment, and never hand-patch an already-applied migration.
- **Before creating a migration:** check for open PRs touching the same tables (`gh pr list`). If overlap exists, merge the in-flight PR first, or rename the new migration to a later timestamp to keep ledger order clean.

The project's migration **toolchain** — CLI commands, production-write protection (DEC-S009), and Supabase↔Vercel env-var sync — lives in `.claude/CLAUDE-context.md` under `## Migration Protocol (project)`. Projects without a database mark it `N/A` there.

## Conventions

Project coding conventions — typing, component structure, data fetching, auth/RLS, error-handling contract, naming, UI/brand, and testing layout — live in `.claude/CLAUDE-context.md` under `## Conventions`. They're stack-specific, so they're project-owned.

## Session Skills

| Skill | When | What |
|-------|------|------|
| `/its-alive` | Session start | Ensure `.sessions-worktree/` exists, open per-session file on orphan `sessions` branch, capture transcript, read context, recommend task |
| `/pause-this` | Mid-session break | Build check, commit WIP on task branch, note pause in session file (sessions branch) |
| `/restart-this` | Resume from pause | Reload context, continue same session |
| `/kill-this` | **Per task** (DEC-S013) | Build check, commit code on task branch, open PR, append `## Task <N>` block to session file. Run N times per session — one per task. No time math. |
| `/its-dead` | Session end (once per window) | Stamp `ended:`, tally points, display wall_clock to screen, close session file. No time math, no version bump (those moved to `/retro`). Merge PRs whenever — order doesn't matter. |
| `/start-phase` | Phase boundary (start) | Materialize phase as Issues with `phase:N`, `points:X` labels |
| `/retro` | Phase boundary (end) | Compute per-session active time (wall − breaks) from `started`/`ended` + transcript break inference. Aggregate one phase velocity (active h/pt). Mark `[x]`, write retro, patch-bump per merged PR + minor-bump at close. |
| `/bump-major` | Breaking change | Manually bump major version. CHANGELOG.md entry + tag on the trunk (`main`). Dev projects only |
| `/promote-production` | Ship trunk to prod | ff-merge `main` → `production` (deploy-only; tag already on the commit), push. Projects with a `production` branch only |
| `/push-seeds` | After workflow improvements | Backport project-side improvements to the seeds templates via @sync-config |
| `/pull-seeds` | After seeds gets new improvements | Pull template changes into this project — schema-version-gated, applied via @sync-config |
| `/read-the-tape` | After a session worth learning from | Audit JSONL transcript, find anti-patterns, propose skill improvements |
| `/doc-consistency-check` | Ad-hoc, when docs feel drifted (no scheduled trigger) | Cross-reference factual claims across `docs/*.md` + root `CLAUDE.md`; flag mismatches + unfilled placeholders. Report-only via @doc-consistency |

**Dev identity:** `~/.claude/devname` (one-line file with handle, e.g. `eric`). Set once per machine.

**Task model:** PROJECT_PLAN.md is read at planning, written at retro. Untouched mid-phase. Current-phase tasks live as GitHub Issues. The phase ends when its issues close.

## Agents

| Agent | Model | When | Purpose |
|-------|-------|------|-------|
| @architect | Opus 4.8 | Before design decisions, new dependencies, scope creep | Coherence vs SPEC + DECISIONS |
| @code-review | Sonnet | After every commit (wired into `/kill-this`) | Catch issues early |
| @pm | Sonnet | Start/end of sessions via skills | Track progress, flag risks |
| @ui-reviewer | Sonnet | After UI work, phase boundaries | Design quality |
| @sync-config | Sonnet | `/push-seeds` and `/pull-seeds` | Classifies template-vs-project diffs, gates structural backports |
| @tape-reader | Sonnet | `/read-the-tape` | Audits session JSONL for workflow anti-patterns |
| @doc-consistency | Sonnet | Via `/doc-consistency-check` skill, or ad-hoc | Cross-reference factual claims across project docs; flag mismatches + unfilled placeholders. Report-only |
| @ideas | Sonnet | Park an idea, re-rank, or audit the parking lot | Curate `docs/FUTURE_IDEAS.md` — capture, dedupe, cross-ref, keep the index. Edits only that file |

## Model Selection

Default to the cheapest model that does the job. **Opus 4.8 is the standing model** for real development and architecture; Sonnet handles cheap/scoped work.

> **Fable is disabled for now (DEC-S029).** The frontier `claude-fable-5` tier and its bundle-then-escalate trigger are withdrawn from this guidance until re-enabled. Everything below routes between Opus (default) and Sonnet (cheap). DEC-S027 retains the prior Fable tiering as history for when it comes back.

| Tier | Model | Use for |
|------|-------|---------|
| Cheap | `claude-sonnet-5` | Trivial/scoped agents and reviews — fast, low-cost. |
| Default | `claude-opus-4-8` | The standing model for development and architecture. Most work runs here. |

- **Reach for `effort` before reaching for a bigger model.** `effort` (`low`/`medium`/`high`/`xhigh`/`max`, via `output_config`) buys quality more cheaply than a model jump on a task the current model can already do. `xhigh` is the floor for coding/agentic work, `high` for intelligence-sensitive work, `max` only when correctness must beat cost.
- **File memory is a force multiplier.** Session files, `design/`, `docs/DECISIONS.md`, and acceptance criteria are the persistent notes the model exploits to improve its own output. Keep them current and reference them explicitly.
- **Agents:** model in agent frontmatter. `@architect` runs Opus 4.8. Reviewers (`@code-review`, `@pm`, `@doc-consistency`, `@tape-reader`) and `@ui-reviewer` stay Sonnet.
- **New agents:** default to Sonnet; pin `model: opus` only when the agent's standing job needs it.

## PR Workflow

- Each task gets a branch: `git checkout -b task/X.Y-short-description`.
- Issues assigned to phase via `phase:N` label (created by `/start-phase`).
- PR title references issue: `closes #N`.
- `/kill-this` opens PR. Self-merge after review unless stakeholder review needed.
- Keep ≤3 open PRs. Prefer 1.
- Never two open PRs with migrations on the same table — merge one first.
- **Stacking PRs is preferred** when tasks depend on each other. Branch the next task off the previous task branch (`git checkout -b task/X.Y-next task/X.Y-prev`), not off main. Only wait for the previous PR to merge when there's a migration conflict on the same table.

### Production branch (DEC-S022)

`main` is the always-active trunk. Every task PRs into `main`; `/retro` patch-bumps per merged PR + minor-bumps at phase close, tagging on `main` immediately. This is the same workflow whether or not the project deploys.

Deployable projects add a `production` branch — a downstream deploy pointer the host (Vercel, etc.) watches. It is **never** a PR base and is never touched by the sync. Ship with `/promote-production`, which ff-merges `main` → `production` and pushes (the version tag is already on the commit from the bump — promotion does not tag).

Adopting a production branch:
```
git checkout -b production main && git push -u origin production
```
Then repoint the host's production branch from `main` to `production` (e.g. Vercel → Settings → Git → Production Branch) — **before** `main` takes active work, or WIP auto-deploys to prod. Removing it: delete the branch and point the host back at `main`. No skill changes to opt in or out — only `/promote-production` cares (it gates on `origin/production`).

## Versioning

Every dev project carries a SemVer version in `package.json`, mirrored to a git tag (`vX.Y.Z`) on `main`. `/retro` is the sole place version bumps happen (DEC-S013 moved patch bumps out of `/its-dead`).

**Three triggers (all run at `/retro` per DEC-S013):**
- **Patch:** `/retro` Step 8.2 — one bump + CHANGELOG entry per PR merged in the phase window. Title pulled from GitHub.
- **Minor:** `/retro` Step 8.3 — at phase close after all patches. CHANGELOG entry summarizes the phase.
- **Major:** `/bump-major` manual. User supplies the breaking-change rationale.

**Tag rule:** tags are applied on the active trunk (`main`) at bump time (DEC-S022). A `production` deploy branch, if present, receives the already-tagged commit via `/promote-production` ff-merge — promotion does not tag.

**Detection:** these skills check `package.json` exists at the repo root before bumping. If it doesn't (template/markdown-only project), they no-op silently.

### `<VersionTag />` component

Build-time version display, reads `process.env.NEXT_PUBLIC_APP_VERSION` + `process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA`. Renders e.g. `v1.2.3 (a1b2c3)`.

Wiring:
- `next.config.ts` (or `next.config.js`) forwards `npm_package_version` → `NEXT_PUBLIC_APP_VERSION`. Critical — without `NEXT_PUBLIC_`, client trees silently render `v0.0.0`.
- Wire into login screen and footer.
- Vercel sets `NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA` automatically. Local `npm run dev` outside Vercel omits the commit hash — that's intentional.

```tsx
import { VersionTag } from "@/components/VersionTag";
<VersionTag className="text-xs text-muted-foreground" />
```

### CHANGELOG.md

Auto-maintained by `/retro` and `/bump-major` (DEC-S013 — `/its-dead` no longer touches it). Don't edit by hand mid-flow — the skills always prepend after the `# Changelog` header. The first bump creates the file if absent.

Format (Keep-a-Changelog inspired but simpler):
```
# Changelog

## [1.2.3] - 2026-05-05
- PR #42: Add login form

## [1.2.2] - 2026-05-04
- PR #41: Fix dashboard query
```

### PR Review on Mobile (developer notes)

Doing PR reviews from your phone is tolerable if you structure for it:
- **GitHub mobile app, not web.** The native app's diff + approve + merge flow is usable. The mobile web is not.
- **Tap the preview URL first.** Vercel posts it as a comment. 60 seconds of clicking the actual feature catches more than reading the diff would.
- **Enable auto-merge.** Repo Settings → enable auto-merge, then "Enable auto-merge" on each PR. Checks pass → it merges itself. One less thing to remember to do.
- **Branch protection:** require CI green (Vercel build + Playwright). Skip reviewer count requirements for solo dev — they add friction with no benefit.
- **Checklist PR descriptions.** `/kill-this` should populate: does this PR have a migration? RLS change? UI change at 375px? A checkbox list is fast to scan on a small screen.
- **`gh` CLI on your dev server** is faster than any UI when you're at a keyboard: `gh pr list`, `gh pr view 42 --web`, `gh pr merge 42 --auto`.

## Workflow Notes
- **Diagnostic commands** (build, lint, type check, test): run directly — see errors, fix them, don't bother the user.
- **Environment-changing commands** (npm install, supabase migrations, git push, deploys): output these for the user to run.
- **Never rebase a task branch that already has commits on origin.** If main has advanced while a PR branch is open, leave the branch as-is — GitHub's "Update branch" button handles this at merge time. Rebasing rewrites remote history and requires a force-push. Use `git merge --ff-only` only if explicitly asked.
- **Debugging CI failures:** Before any multi-step local debug (spawning servers, reading cookies, modifying middleware), confirm the environment is functional: "Can you run the test suite locally right now? What env vars are set?" One environmental check before any code change.
- **JSON parsing in Bash:** Prefer `gh ... --jq '...'` (built-in jq via `gh`) or `jq` over `python3 -c "import json,sys; ..."` one-liners. The python invocations trigger per-pattern permission prompts (each unique argument list is a new allowlist entry), while `gh --jq` runs under the existing `Bash(gh ...)` allowance. For non-`gh` JSON, install/use `jq` directly. Reserve python for cases where the data shape genuinely needs control flow.
- **Bug reports:** create a GitHub issue, label `bug`, add to current or next phase.

Project-specific debugging gotchas (dev-server checks, stale-process traps, auth-redirect quirks) live in `.claude/CLAUDE-context.md` under `## Workflow Notes (project)`.

## Approval Before Action (all tasks)

For every task — not just bugs — explain the plan and wait for approval before doing anything:
1. State what files you'll create or modify and why
2. List commands you'll run, especially commits, pushes, package installs,
   anything touching production
3. Wait for "go", "do it", or equivalent
4. Do not edit files or run commands until approved

## Bug Reports & Questions
When a bug is reported or a question is asked:
1. Explain the cause and your proposed fix
2. Wait for approval before making any changes
3. Do not edit files, run commands, or implement fixes until given the go-ahead

## Scope Discipline
Check `docs/SPEC.md` "Not V1" before adding anything.

If a task feels bigger than its estimate:
1. Stop, re-estimate
2. Update PROJECT_PLAN.md (at next phase boundary, or via Issue if mid-phase)
3. If scope creep, flag and move on

**Splitting is a reviewability call, not a model-capability one.** Points size *estimation*; they don't cap how much gets built in one run. A capable model holds coherence across far more than an 8, and splitting a *coherent* task fragments context — two stitched-together 5s can land worse than one well-specified 8. So:
- **Don't split a coherent 8** (one feature, one migration, one subsystem) just to honor a ceiling — run it as one unit with the full spec up front.
- **Do split** when the diff is too large to review well, the blast radius or reversibility worries you, there's a migration conflict (see PR Workflow), or an "8" is secretly two unrelated things.
- **Still break genuine 13s** — for review and risk, and because a 13 usually means the task isn't understood well enough yet. Not because the model can't hold it.
- Larger units lean harder on a complete spec + crisp ACs and the `@architect` gate. Raise the ceiling only with those in place.

## Tone
Occasional dry humor and sarcasm welcome. One good line beats three forced ones.

## Response Length

Default to the shortest response that fully answers — usually 2–5 sentences. No preamble, no restating the question, no closing offers to help further. No reflexive "let me know if you need more" or "happy to expand." Do offer concrete follow-ups when they'd save a future round-trip. Length is requested explicitly ("expand," "give me the long version"), never the default.

Be meticulous and skip disclaimers.

## Verbosity

End-of-turn summaries: one or two sentences. What changed, what's next. Stop there.

Do not recap work I just watched you do. Do not restate the task. Do not explain why an obvious step was obvious. The summary exists so I can re-enter context next session — not so you can demonstrate effort.

If a turn ends with a tidy bullet list followed by three paragraphs of prose, the prose is wrong. Delete it.

Mid-session updates: one sentence per state change. "Found X." "Switching to Y." "Build green." Not a paragraph.

This rule applies double at session end. The session-summary block is the first thing I read next session — make it dense, not voluminous. Five bullets of work and a wall of text means I cannot actually use the summary. Cut the wall.

## Narration

`Response Length` and `Verbosity` above are the standing baseline. This is the switchable knob on top of them — Opus 4.8 narrates more by default, so name the level and I'll hold it for the session.

- **Terse** (default): Silence between tool calls. One sentence only when I find something, change direction, or hit a blocker. No "Now I'll…", "Let me check…", "Looking at…", no recapping what you just watched. Close with one or two sentences on the outcome.
- **Normal**: Brief progress notes at meaningful steps — not every action.
- **Narrate**: Explain reasoning as I go. For teaching, debugging, or watching a tricky change land.

Switch any time: `narration: terse|normal|narrate`.

Two mechanics move narration the same direction, independent of level:
- **Keep adaptive thinking on.** With thinking disabled, 4.8 spills reasoning into the visible answer — which reads as *more* narrative. Adaptive keeps reasoning in thinking blocks and the response clean.
- **Lower `effort`** (`low` / `medium`) trims preamble and confirmations — a coarser lever than the levels above.

## Cost and Waste

Never minimize cost. Banned phrasings include but are not limited to:
- "essentially zero"
- "negligible"
- "only a few cents"
- "just X dollars"
- "a rounding error"
- "not a big deal"
- "don't worry about it"

If you find yourself reaching for one, stop. Any synonym counts. If the function of the phrase is to minimize, it's banned.

It's my money. Willing-to-spend is not the same as willing-to-spend-flippantly. Treat every cost as real, including small ones. Same rule for compute, API calls, third-party services, and dependencies — anything that consumes resources I'm paying for.

Waste of any kind — food thrown out, hours lost, a bad batch, a bricked migration, an over-provisioned instance, a wrong dependency pulled — is a fact, not a problem to console me about. When I tell you something had to be discarded, do not reassure me it's fine. Acknowledge it and move on.

If you catch yourself about to write a reassurance, just don't. The fact is the fact.
