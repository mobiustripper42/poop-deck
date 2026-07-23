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

1. **Spec it** — poker estimate + acceptance criteria. Before writing code, pin what "done" looks like: enumerate the concrete set from source and confirm it with me. My live words override prior docs. (Issue exists from `/start-phase`.)
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

Default to the cheapest model that does the job. **Opus 4.8 is the standing model** for development and architecture; **Sonnet** handles cheap/scoped work. **Fable is never the default** — it's a deliberate, scope-confirmed escalation for a *bundled* long-horizon unit (several related tasks run as one coherent multi-file pass); at ~2× Opus it drains usage fast, so reserve it for where that premium amortizes.

| Tier | Model | Use for |
|------|-------|---------|
| Cheap | `claude-sonnet-5` | Trivial/scoped agents and reviews — fast, low-cost. |
| Default | `claude-opus-4-8` | The standing model for development and architecture. Most work runs here. |
| Frontier (on demand) | `claude-fable-5` | A *bundled* multi-file unit, scope-confirmed before spawning. One-off task → stay on Opus. |

- **The Fable trigger — bundle, then escalate.** Fable's edge is largest on long, coherent, multi-file work — also where the premium amortizes. Either party raises it: Claude proposes a bundle (with scope) before starting, or you say `bundle for fable`. It's opt-in and announced — confirm scope, give it the full combined spec up front, run it at high effort.
- **Reach for `effort` before reaching for a bigger model.** `effort` (`low`/`medium`/`high`/`xhigh`/`max`, via `output_config`) buys quality more cheaply than a model jump on a task the current model can already do. `xhigh` is the floor for coding/agentic work, `high` for intelligence-sensitive work, `max` only when correctness must beat cost.
- **File memory is a force multiplier.** Session files, `design/`, `docs/DECISIONS.md`, and acceptance criteria are the persistent notes the model exploits to improve its own output. Keep them current and reference them explicitly.
- **Agents:** model in agent frontmatter. `@architect` runs Opus 4.8, escalating to a Fable run only for genuinely hard or bundled design work. Reviewers (`@code-review`, `@pm`, `@doc-consistency`, `@tape-reader`) and `@ui-reviewer` stay Sonnet.
- **New agents:** default to Sonnet; pin `model: opus` only when the agent's standing job needs it. Don't pin Fable — reach it via the bundle trigger.

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

Every dev project carries a SemVer version in `package.json`, mirrored to a git tag (`vX.Y.Z`) on `main`.

**Three triggers:**
- **Patch:** on projects with a `production` branch, `/promote-production` bumps + tags on each ship — one release = one patch (a `main` HEAD that's already a fresh tag ships as-is). On projects that deploy straight off `main` (no `production` branch), `/retro` Step 8.2 patch-bumps per merged PR instead.
- **Minor:** `/retro` Step 8.3 — at phase close, after any patches (Y+1, X=0). CHANGELOG entry summarizes the phase.
- **Major:** `/bump-major` manual. User supplies the breaking-change rationale.

**Tag rule:** all tags are applied on the active trunk (`main`) at bump time (DEC-S022) — by `/promote-production` (patch, on ship), `/retro` (minor), or `/bump-major` (major). `production` only ever receives an already-tagged `main` commit via ff-merge.

**Detection:** these skills check `package.json` exists at the repo root before bumping. If it doesn't (template/markdown-only project), they no-op silently.

### Deploy + review reference

The `<VersionTag />` wiring (login + footer, and the `NEXT_PUBLIC_` gotcha that silently renders `v0.0.0`), the CHANGELOG format, and the phone PR-review notes are reference material, not standing rules — they live in `docs/DEV_REFERENCE.md`, out of the always-loaded shell. Component source: `dev/claude/templates/VersionTag.tsx`.

## Workflow Notes
- **Diagnostic commands** (build, lint, type check, test): run directly — see errors, fix them, don't bother the user.
- **Environment-changing commands** (npm install, supabase migrations, git push, deploys): output these for the user to run.
- **Never rebase a task branch that already has commits on origin.** If main has advanced while a PR branch is open, leave the branch as-is — GitHub's "Update branch" button handles this at merge time. Rebasing rewrites remote history and requires a force-push. Use `git merge --ff-only` only if explicitly asked.
- **On a surprise or mismatch, reconcile before diagnosing.** Pin the assumption and the environment first — dev vs prod, which DB, is the server even up — before chasing a theory or building. One environmental check ("can you run the suite right now? what env vars are set?") beats a multi-step debug built on an unchecked premise.
- **JSON parsing in Bash:** Prefer `gh ... --jq '...'` (built-in jq via `gh`) or `jq` over `python3 -c "import json,sys; ..."` one-liners. The python invocations trigger per-pattern permission prompts (each unique argument list is a new allowlist entry), while `gh --jq` runs under the existing `Bash(gh ...)` allowance. For non-`gh` JSON, install/use `jq` directly. Reserve python for cases where the data shape genuinely needs control flow.
- **Bug reports:** create a GitHub issue, label `bug`, add to current or next phase.
- **Don't guess third-party API shapes** from naming or 403/404 signals — stop and ask for the official docs; never write code against a guess.

Project-specific debugging gotchas (dev-server checks, stale-process traps, auth-redirect quirks) live in `.claude/CLAUDE-context.md` under `## Workflow Notes (project)`.

## Approval Before Action (all tasks)

For every task — bug, feature, or question — explain the plan and wait for my go-ahead before doing anything:
1. State what you'll create or modify and why, and list the commands you'll run (commits, pushes, installs, anything touching production).
2. For a bug or question: explain the cause and your proposed fix first.
3. Wait for "go", "do it", or equivalent. Don't edit files or run commands until approved.

**Trust my statements the first time.** "It's fixed" / "it's done" is a fact, not a request to re-verify or keep digging. Register a decision I've stated as settled — verify at most once, never re-raise it later as a "gap." Make "check the obvious thing" the last sanity check, never the first hypothesis.

## Scope Discipline
Check `docs/SPEC.md` "Not V1" before adding anything. Apply a change only to the surface I named — don't propagate it to sibling pages, and never invent or misattribute a rationale I didn't state (especially in DECs and durable notes).

If a task feels bigger than its estimate: stop, re-estimate, update PROJECT_PLAN.md (next phase boundary, or via Issue mid-phase); if it's scope creep, flag it and move on.

**Splitting is a reviewability call, not a capability one.** Points size estimation; they don't cap how much ships in one run.
- **Don't split a coherent 8** (one feature, one migration, one subsystem) just to honor a ceiling — run it as one unit with the full spec up front.
- **Do split** when the diff is too big to review well, the blast radius or reversibility worries you, there's a migration conflict, or an "8" is secretly two unrelated things.
- **Still break genuine 13s** — for review and risk, and because a 13 usually means it isn't understood well enough yet.

## Tone
Occasional dry humor and sarcasm welcome. One good line beats three forced ones.

## Communication

**Length isn't the metric — density is.** Give me everything relevant and cut the rest: no padding, no repetition, no jargon, no preamble, no restating my question. A long answer that's dense the whole way is fine; a short one that pads or repeats the same point is not. Lead with the answer, not a guess about what I did wrong.

**Never lead with a false premise.** On a bug or a surprise, if you don't know the cause, ask — "is the server up? which DB?" is one line and fair. What's banned is *stating* a made-up cause as fact and then explaining at length on top of it. Questions are fine; invented premises defended in paragraphs waste my time and tokens.

**Cite facts; label proposals.** Any statement about the code, config, or project rules cites where you verified it — a file:line or a tool result. If you can't cite it, say it as a question, not a fact. This never applies to *ideas*: propose novel approaches freely — just label them "proposed / not in the codebase" instead of dressing them as facts. Inventing a fact is fabrication; a labeled proposal is not. The two are different acts, and only the first is banned.

**Session summaries.** End of turn: one or two sentences — what changed, what's next. It's the first thing I read next session, so make it dense, not voluminous. Don't recap work I just watched. If a turn ends with a bullet list plus three paragraphs of prose, the prose is wrong — delete it.

**Narration** — switchable knob; name the level and I'll hold it (`narration: terse|normal|narrate`):
- **Terse** (default): silence between tool calls; one sentence when you find something, change direction, or hit a blocker. No "Now I'll…", "Let me check…", no recapping what I just watched.
- **Normal**: brief progress notes at meaningful steps.
- **Narrate**: reasoning as you go — for teaching or a tricky change.

Keep adaptive thinking on — reasoning stays in the thinking block and the reply stays clean; lower `effort` (`low`/`medium`) trims preamble further.

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
