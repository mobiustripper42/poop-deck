# poop-deck — Project Context

Everything specific to **this** project. The seeds-managed `CLAUDE.md` shell reads this file at session start and treats it as authoritative for project-specific facts (DEC-S019). This is a **`tool`** project (Postgres store + Python ingest daemons + Grafana provisioning), so the shell's webapp defaults — Playwright/pgTAP, Supabase migrations, 375px screenshots, `<VersionTag />`, `@ui-reviewer` — are overridden or N/A below. Nothing here syncs from seeds.

## What We're Building

**Poop Deck** is Bay Branch Farm's **shared telemetry backend** — a TimescaleDB/Postgres store with Grafana graphing, fed over MQTT. Each producer publishes JSON into its own topic namespace and its own hypertable; Poop Deck validates, inserts idempotently, logs, drops anything malformed, and **never computes** (DEC-001). It already ingests **tinkle** (irrigation); it becomes the store + dashboard for **soundings** (soil sensors) and later weather.

It is one component of the farm's larger recording/analysis picture: a single relational store is what lets soil tension, irrigation runs, weather, and the farm's own records (yield, fertigation, journal) be JOINed together. That JOIN requirement is why the store is Postgres, not a bare metrics TSDB (DEC-003).

**Sibling projects (producers):**
- **tinkle** — the farm's irrigation controller (separate repo; firmware built). An *event* producer: publishes run-complete events to `farm/irrigation/tinkle/zone<N>`. Its schema + ingest daemon are the seed this repo starts from.
- **soundings** — a LoRa soil/air sensor mesh (separate repo; software-first, mid-build). A *sensor* producer: its gateway will derive kPa/VPD and publish **raw + derived** JSON to `farm/soundings/…`. Onboarded in Phase 2 after its server-breakout.

The boundary to every producer is **one-way** (DEC-002): producers publish; nothing here reads back into a producer, and no producer reads another's data except through a query to this store.

## Project Type

`tool` — a Postgres/Timescale store + Python ingest daemons + Grafana provisioning. **Not a webapp.** No Supabase, Next.js, React, RLS, or Playwright. **Grafana is the only UI**, so `@ui-reviewer` and `VersionTag.tsx` are intentionally absent (gated out for `tool` type, DEC-S011 in seeds).

## Build Philosophy

- **Dumb store, never computes (DEC-001).** Validate → insert → log → drop bad. Producers own their physics.
- **One-way, per-producer (DEC-002).** Cross-links go through the store as a query, never a repo link. A Poop Deck outage is a dropped publish, nothing worse.
- **Idempotent by construction (DEC-004).** Natural-key `ON CONFLICT DO NOTHING` on every table; redelivery and replay are no-ops.
- **Validate-and-drop, never-crash (DEC-004).** A poison message logs and drops; it never kills the daemon.
- **Storage shape by producer kind (DEC-005).** Semantic columns for event producers (tinkle); raw **+** derived for sensor producers (soundings).
- **Keep raw forever.** Readings/events are tiny; no downsampling.

## Stack

- **Broker:** Mosquitto (MQTT), `1883`. Topics `farm/<producer>/…`.
- **Store:** **TimescaleDB** (PostgreSQL + hypertables). Resolves soundings' D6 (DEC-003).
- **Dashboards:** Grafana (the only UI). Producers provision their own dashboards/alerts in from their repos; Poop Deck owns the shared instance + overview dashboards.
- **Ingest:** one small always-on Python daemon per producer — `paho-mqtt` + `psycopg[binary]`. Config via env (`MQTT_HOST`, `MQTT_PORT`, `PG_DSN`).
- **Runtime:** `docker-compose` on a laptop for dev/sim; the same shape on the farm's headless box (the Beelink) for prod.

## Repo Layout

```
db/migrations/    Ordered SQL applied to Timescale (the schema ledger). One hypertable
                  per producer; each ships with its natural-key unique index.
ingest/           One dumb Python ingest daemon per producer (validate → insert → log → drop).
deploy/           docker-compose for the stack (Mosquitto + TimescaleDB + Grafana). — Phase 1
dashboards/       Grafana definitions Poop Deck owns (shared / overview / tinkle).
docs/             SPEC, DECISIONS, PROJECT_PLAN, RETROSPECTIVES, AGENTS, velocity guide.
docs/reference/   Reference producer implementations (e.g. tinkle's publisher snippet).
```

**Staged now (Phase-1 substrate, not yet wired):** `db/migrations/0001_irrigation_runs.sql` and `ingest/irrigation_ingest.py`, both from the tinkle handoff.

## Architecture

Producers publish JSON over MQTT into per-producer topics; a per-producer ingest daemon subscribes, validates against the contract, and writes into that producer's hypertable. The store is dumb — no derivation anywhere in the ingest path. The one contract (DEC-004): `v`-versioned JSON, natural-key idempotency, validate-and-drop, never-crash. Storage shape follows producer kind (DEC-005).

## Commands

```bash
# Stack (from repo root) — Phase 1 onward
docker compose -f deploy/docker-compose.yml up -d     # broker + Timescale + Grafana
docker compose -f deploy/docker-compose.yml down

# Apply / inspect schema (against the compose Postgres)
psql "$PG_DSN" -f db/migrations/0001_irrigation_runs.sql
psql "$PG_DSN" -c '\d+ irrigation_runs'

# Run an ingest daemon
MQTT_HOST=localhost PG_DSN=postgresql://poopdeck@localhost/farm python ingest/irrigation_ingest.py

# Ingest tests (Python)
#   venv:  python3 -m venv .venv && .venv/bin/pip install pytest paho-mqtt 'psycopg[binary]'
.venv/bin/python -m pytest
```

(Commands firm up as Phase 1 lands the compose file and the daemon wiring.)

## Additional Docs

| File | Purpose |
|------|---------|
| `docs/reference/tinkle_publish.ino` | Reference producer — the canonical shape of a conformant Poop Deck publisher (tinkle owns the authoritative copy) |

Baseline docs the shell lists that **don't apply here** (embedded/backend tool, no UI): no `docs/BRAND.md`, `docs/USER_STORIES.md`, or `docs/CHEATSHEET.md`. `docs/RETROSPECTIVES.md` uses **throughput velocity (DEC-S026)**.

## Workflow Overrides

The shell's `## Micro Workflow` is webapp-shaped (Playwright + pgTAP + 375px screenshot). Poop Deck is a Postgres store + Python ingest daemons — those steps are replaced by:

- **Step 5 (Write the test):** `pytest` for ingest logic (validate-and-drop, unknown-`v` drop, natural-key idempotency / redelivery-is-a-no-op). SQL smoke checks for a new migration (hypertable + unique index exist; a duplicate insert is a no-op). No Playwright, no pgTAP.
- **Step 6 (Run targeted tests):** `.venv/bin/python -m pytest tests/test_foo.py`; escalate to the compose stack + a synthetic publisher for full end-to-end. Don't run a long/full suite without saying so first.
- **Step 7 (Mobile screenshot):** N/A — the only UI is Grafana dashboards.
- **`No test, no push.`** Run targeted tests freely during development.

## Migration Protocol (project)

The shell's `## Migration Protocol` **discipline** holds (migrations are the source of truth; never patch an applied migration or edit schema through a dashboard). The **toolchain is plain SQL, not Supabase:**

- Schema changes are **ordered SQL files in `db/migrations/`** (`NNNN_descriptive_name.sql`), applied in filename order against the Timescale store (via `psql`, or the compose init that replays the directory).
- A new hypertable ships with its `create_hypertable(...)` **and** its natural-key unique index in the **same** file (idempotency is not a follow-up — DEC-004).
- Before adding a migration, check for open PRs touching the same table (`gh pr list`); if overlap, merge the in-flight PR first or renumber to a later ordinal.
- **Supabase/Vercel bits are N/A:** no `supabase` CLI, no `safe-supabase.sh` guard (DEC-S009), no Vercel env-sync. The one production-write hazard is `psql`/daemon against the farm's real Postgres — treated under `## Approach to Action`, not a wrapper script.

## Conventions

- **The store never computes (DEC-001).** No derivation in a migration, a daemon, or a view beyond retention. If you're tempted to convert or roll up producer physics, stop — that's the producer's job.
- **Idempotent inserts (DEC-004).** `INSERT … ON CONFLICT (<natural key>) DO NOTHING`. A redelivered or replayed message must be a no-op.
- **Validate-and-drop, never-crash (DEC-004).** Missing required fields / bad JSON / unknown `v` → log at WARNING and drop. DB error → roll back and continue. Never raise out of the message handler.
- **Schema-versioned payloads.** Every payload carries `v`; branch on it; drop unknown versions.
- **Storage shape by kind (DEC-005).** Semantic for events, raw+derived for sensors. Pick the natural key per producer at onboarding (@architect).
- **Python style:** type hints, stdlib-first, `paho-mqtt` + `psycopg`. Handle malformed input gracefully and log it — never crash the daemon on bad data. Config via env, not literals (DSNs, broker host, topic prefixes).
- **SQL style:** one migration = one coherent change; comments explain *why* (the query you'll actually run, the retention rationale), as in the staged irrigation schema.
- **Pin every container image** in the compose file.

## Testing

- **Ingest (pytest):** the load-bearing tier — validate-and-drop, unknown-`v` drop, natural-key dedup, never-crash-on-poison. Inject a fake DB/broker seam so it runs without live services.
- **SQL smoke:** a fresh migration creates the hypertable + unique index; a duplicate insert is a no-op.
- **End-to-end:** compose stack + a synthetic publisher → daemon → Timescale → dashboard moves; idempotent replay proven. No hardware.

## Versioning (project)

**No `package.json`**, so the shell's version-bump steps in `/retro` / `/bump-major` no-op silently. `<VersionTag />` is N/A (Grafana is the UI). Payloads carry their own `v` schema-version — that's the versioning that matters operationally; a repo version surface can be added later if wanted.

## PR Workflow (project)

Follows the shell. **No `production` branch** unless a deployable surface appears — PRs ship to `main`; only `/promote-production` cares and it gates on `origin/production` (DEC-S022). Stacking PRs is preferred for dependent tasks. Never two open PRs with migrations on the same table — merge one first.

## Model Selection

Follows the shell's `## Model Selection` **as-is (DEC-S029):** Opus 4.8 is the standing model, Sonnet for cheap/scoped work. **Fable is disabled** — do not route to `claude-fable-5`. `@architect` is pinned to Opus 4.8 (`.claude/agents/architect.md` frontmatter). Reach for `effort` before a bigger model; `xhigh` is the floor for coding/agentic work.

## Approach to Action (project override)

**This overrides the shell's `## Approval Before Action` / `## Bug Reports & Questions` gates.** Poop Deck defaults to action: for non-trivial or destructive *local* work, say what you're about to do and why in a sentence, then proceed — **don't stall for approval on local, reversible steps** (compose up/down on a laptop, migrations against the *local* Timescale, tests, file edits, synthetic publishes).

Reserve explicit confirmation for the genuinely consequential: **any write against the farm's real production Postgres or broker, a deploy to the Beelink, force-pushes, and anything touching shared/remote state or hard to reverse.** This is an always-on store other systems depend on — production data integrity is the thing to be careful with, not a local `docker compose down`.

Check `docs/SPEC.md` "Not V1 / never here" before adding scope — especially anything that would have the store *compute*. If a task feels bigger than its estimate: stop, re-estimate; if it's scope creep, flag and move on.
