# Poop Deck

The farm's **shared telemetry backend** — a TimescaleDB/Postgres store with Grafana graphing, fed over MQTT. It is a **dumb store**: it validates a payload, writes it, logs it, and drops anything malformed. It never computes. Producers own their own physics and derivation; Poop Deck just remembers.

```
producer  →  MQTT (farm/<producer>/…)  →  ingest daemon  →  TimescaleDB hypertable  →  Grafana
                                          (validate → INSERT … ON CONFLICT DO NOTHING → log+drop bad → never crash)
```

Each producer publishes JSON into its **own** topic namespace and its **own** hypertable. No producer reads another's data directly — cross-links happen *through* Poop Deck as a query, never as a repo link (one-way, per-producer). A Poop Deck outage is a dropped publish for a producer, nothing worse; every producer stays autonomous when Poop Deck is dark.

## Producers

| Producer | Kind | Publishes | Storage shape | Status |
|----------|------|-----------|---------------|--------|
| **tinkle** (irrigation) | event | `farm/irrigation/tinkle/zone<N>` | semantic (gallons, duration) | schema + daemon staged; wired in Phase 1 |
| **soundings** (soil sensors) | sensor | `farm/soundings/…` | raw **+** derived (raw counts durable, kPa/VPD recomputable) | Phase 2 (after soundings breakout) |
| weather (Davis) | poll | — | semantic | later |

## Repo layout

```
db/migrations/   Ordered SQL applied to the Timescale store (the schema ledger).
ingest/          One dumb Python ingest daemon per producer (paho-mqtt + psycopg).
deploy/          docker-compose for the stack (Mosquitto + TimescaleDB + Grafana). — Phase 1
dashboards/      Grafana dashboard definitions hosted here (shared/overview). Each
                 producer owns ITS own dashboards/alerts in ITS repo, provisioned in.
docs/            SPEC, DECISIONS, PROJECT_PLAN, and the ingest contract.
docs/reference/  Reference producer implementations (e.g. tinkle's publisher snippet).
```

## Status

**Phase 0 — scaffold.** The repo describes the real project and has a documented home for every kind of code. The tinkle schema and ingest daemon are staged (`db/`, `ingest/`) but **not yet stood up** — standing up the stack, wiring tinkle, and building the irrigation dashboard is Phase 1. See `docs/PROJECT_PLAN.md`.

Start a work session with `/its-alive`. Read `.claude/CLAUDE-context.md` for the full picture.
