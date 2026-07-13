# Poop Deck — Specification

*Bay Branch Farm's shared telemetry backend. This SPEC is a guide to keep us on track, not a contract. It disagrees with reality → reality wins and the SPEC gets updated.*

---

## 1. What Poop Deck is

**Poop Deck** is the farm's shared telemetry backend — a **TimescaleDB/Postgres** store with **Grafana** graphing, fed over **MQTT**. It already ingests **tinkle** (irrigation). It becomes the datastore + dashboard for **soundings** (soil sensors), and later weather and whatever else the farm grows.

Each producer publishes JSON over MQTT into its own topic namespace and its own hypertable. Poop Deck is a **dumb store**: it validates, inserts idempotently, logs, and drops anything malformed — and it **never computes** (DEC-001). Producers own their own physics and derivation.

**The one-sentence pipeline:**

```
producer  →  MQTT (farm/<producer>/…)  →  ingest daemon  →  TimescaleDB hypertable  →  Grafana
```

**Primary goal:** be the durable, correlatable home for every farm signal — so that soil tension, irrigation runs, and weather can sit in one store and be JOINed against the farm's other records. Boring, always-on, hard to knock over.

---

## 2. Philosophy

- **Dumb store, never computes (DEC-001).** Validate → insert → log → drop bad. Producers derive; Poop Deck remembers.
- **One-way, per-producer (DEC-002).** No producer reads another's data directly. Cross-links go through the store as a query. A Poop Deck outage is a dropped publish, nothing worse — every producer stays autonomous when Poop Deck is dark.
- **Idempotent by construction (DEC-004).** Natural-key `ON CONFLICT DO NOTHING` everywhere. Redelivery and replay are no-ops, never double-counts.
- **Resilient by default (DEC-004).** A daemon logs and drops bad input; it does not crash. A poison message must never take down ingest.
- **Keep raw forever.** Events and readings are tiny (a run every 15 min all season ≈ 4k rows/year). No downsampling, no TTL. Disk is not the arm with a problem.
- **Farm-owned, no cloud, no subscription.** Mosquitto + TimescaleDB + Grafana on the farm's own headless box. Both ends of every link are ours.

---

## 3. The ingest contract

The single contract every producer honors (full reasoning in DEC-004):

| Property | Rule |
|----------|------|
| **Transport** | JSON over MQTT |
| **Topic** | `farm/<producer>/…` — one namespace per producer |
| **Versioning** | every payload carries `v` (integer). Unknown `v` → drop, never best-effort parse |
| **Idempotency** | each hypertable declares a natural key; ingest is `INSERT … ON CONFLICT (key) DO NOTHING` |
| **Validation** | required fields missing / bad JSON → log at WARNING and drop |
| **Resilience** | DB error → roll back and continue; never crash the daemon |

The canonical example of a conformant publisher is tinkle's `docs/reference/tinkle_publish.ino` (fire-and-forget, QoS 0, `farm/irrigation/tinkle/zone<N>`, `v:1`).

---

## 4. Storage shape — by producer kind (DEC-005)

| Producer kind | Example | Stored as | Natural key |
|---------------|---------|-----------|-------------|
| **Event** | tinkle irrigation | **semantic** columns (`gallons`, `duration_s`) — the fields *are* the fact | `(source, zone, ts_start)` |
| **Sensor** | soundings soil | **raw + derived** — raw counts are the durable record, kPa/VPD are a re-revisable lens stored alongside | `(node_id, seq)` or `(node_id, channel, received_at)` |

**The load-bearing rule:** do **not** copy the semantic-only irrigation schema onto sensor tables. `soundings_readings` must carry raw per-channel counts **and** derived columns — the soundings gateway already puts raw on the wire, and raw is what keeps the derivation re-revisable.

---

## 5. Scope

### In for V1

- The stack: a pinned `docker-compose` of **Mosquitto + TimescaleDB + Grafana**, mirroring the farm box's shape, runnable on a laptop.
- **tinkle ingest** — the irrigation hypertable (`db/migrations/0001_irrigation_runs.sql`) + the dumb ingest daemon (`ingest/irrigation_ingest.py`), both staged and ready to wire.
- **The tinkle irrigation dashboard** — gallons/minute by zone (to catch the far-end under-delivery already suspected from the EC gradient), per-zone runs, fault surfacing.
- Then, in order: **soundings readings** (raw + derived), then **weather** (Davis WeatherLink).

### Not V1 / never here

- **Poop Deck computing anything** (DEC-001). Derivation belongs to producers. This is not a "V1 vs later" line — it's a permanent boundary.
- **Producer-to-producer coupling** (DEC-002). A consumer queries the store; it does not link another producer's repo.
- **Actuation / control.** Poop Deck is a store. It never drives a valve, a pump, or anything else. (tinkle actuates; Poop Deck records that tinkle did.)
- **A producer's alert/dashboard *definitions* living here.** Each producer owns its own dashboards + alert rules as versioned config in its own repo, provisioned *into* the shared Grafana (DEC-004, soundings-side of the handoff). Poop Deck hosts the shared instance and owns only cross-producer/overview dashboards.
- **A custom web UI.** Grafana is the UI. This is a `tool` project, not a webapp.

---

## 6. Producers

| Producer | Kind | Topic namespace | Table | Status |
|----------|------|-----------------|-------|--------|
| **tinkle** (irrigation controller) | event | `farm/irrigation/tinkle/zone<N>` | `irrigation_runs` | schema + daemon staged; wired in Phase 1 |
| **soundings** (LoRa soil/air sensor mesh) | sensor | `farm/soundings/…` | `soundings_readings` (raw + derived) | Phase 2, after the soundings server-breakout |
| weather (Davis Vantage Vue via WeatherLink) | poll | TBD | TBD | later |

---

## 7. Deployment

- **Development / sim:** the whole stack on a laptop via `deploy/docker-compose.yml`. A synthetic publisher drives the pipeline end-to-end with no hardware.
- **Production:** the same shape on the farm's headless box (the Beelink). Writes to the real store are the one genuinely consequential operation — treat prod DB/broker with care (`.claude/CLAUDE-context.md § Approach to Action`).

---

*This spec is a guide. When it disagrees with what the store or the farm teaches us, reality wins and the spec gets updated.*
