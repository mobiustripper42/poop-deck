# Poop Deck — Project Plan

**Critical path:** be the durable store + dashboard for the farm's signals. tinkle ingest live first (its schema + daemon are ready), then soundings readings at the soundings server-breakout, then weather. This plan is read at planning and written at retro — not edited mid-phase. Current-phase tasks live as GitHub Issues (DEC-S013).

---

## Estimation Method

Fibonacci points (2, 3, 5, 8, 13). No 1s (just do it), avoid 13s (break them down). Tests are baked into every estimate — no separate testing tasks. Velocity is tracked as **throughput (points per calendar week)** at phase boundaries (DEC-S026), not hours/point. See `VELOCITY_AND_POKER_GUIDE.md`.

**Velocity baseline:** not yet established.

---

## Build Order

Stand the store up around the producer that's already ready (tinkle), prove the whole dumb-store contract end-to-end, then onboard producers one at a time behind the same contract.

### Phase 0 — Scaffold *(this session)*

Get the project onto correct footing: seeds `tool` tooling, a SPEC + DECISIONS that describe the real project, a documented repo layout, and the tinkle schema + daemon staged into place. No stack stood up, no code wired.

**Done when:** the repo describes the real project and has a documented home for every kind of code; the tinkle seed (schema + daemon) is staged and labeled as Phase-1 substrate. *(In progress.)*

### Phase 1 — Stand up the stack + ingest tinkle

The thinnest real end-to-end slice: the compose stack up, the irrigation hypertable applied, the tinkle daemon ingesting idempotently, and the irrigation dashboard moving. tinkle is chosen first because its schema and daemon already exist (in the zip) — the work is wiring and standing up, not authoring.

**Done when:** a published irrigation event lands in Timescale through the dumb daemon and shows on the tinkle dashboard, and a replayed/duplicate event is a proven no-op.

| Task | Description | Points | Issue |
|------|-------------|--------|-------|
| 1.1 | `deploy/docker-compose.yml` — Mosquitto + TimescaleDB + Grafana, pinned images, env, volumes, Timescale init that applies `db/migrations/`. Stack comes up clean on a laptop. | 3 | [x] [#2](https://github.com/mobiustripper42/poop-deck/issues/2) |
| 1.2 | Apply + verify the irrigation schema — hypertable created, `(source, zone, ts_start)` unique index present, the gallons/min query from the schema comment runs. | 2 | [x] [#3](https://github.com/mobiustripper42/poop-deck/issues/3) |
| 1.3 | Wire the tinkle ingest daemon against the stack — env (`MQTT_HOST`, `PG_DSN`), pytest for the validate-and-drop + idempotency logic (missing fields dropped, unknown `v` dropped, redelivery a no-op). | 3 | [x] [#4](https://github.com/mobiustripper42/poop-deck/issues/4) |
| 1.4 | Tinkle irrigation dashboard — gallons/min by zone, per-zone run history, fault surfacing. Phone-usable. Lives in `dashboards/`, provisioned into Grafana. | 5 | [x] [#5](https://github.com/mobiustripper42/poop-deck/issues/5) |
| 1.5 | End-to-end proof — a synthetic tinkle publisher → daemon → Timescale → dashboard moves; idempotent replay demonstrated. | 3 | [x] [#6](https://github.com/mobiustripper42/poop-deck/issues/6) |

**Phase 1 total: 16 points.**

### Phase 2 — soundings readings (raw + derived)

Onboard the soundings sensor mesh behind the same contract. The `soundings_readings` hypertable carries **raw per-channel counts + derived kPa/VPD** (DEC-005), keyed `(node_id, seq)`. A soundings ingest daemon subscribes `farm/soundings/…`. soundings' own dashboards + alert rules provision *in* from the soundings repo.

**Done when:** the soundings gateway publishes raw+derived JSON that lands in `soundings_readings`, and a soundings dashboard renders it. Gated on the soundings server-breakout (retire its VictoriaMetrics + Grafana, swap its `ingest.py` writer to publish here).

> **Provisional — re-poker at `/start-phase`.** Task shapes depend on the soundings breakout landing.

| Task | Description | Points |
|------|-------------|--------|
| 2.1 | `soundings_readings` migration — raw + derived columns, natural key `(node_id, seq)`, idempotent. | ~3 |
| 2.2 | soundings ingest daemon — subscribe `farm/soundings/…`, validate-and-drop, idempotent insert of raw+derived. | ~3 |
| 2.3 | Provision soundings' repo-owned dashboards/alerts into the shared Grafana. | ~3 |

**Phase 2 coarse total: ~9 points (provisional).**

### Phase 3 — weather (Davis)

Pull Davis Vantage Vue data (via WeatherLink Live's local HTTP JSON) into a weather hypertable beside the sensor data, so weather JOINs the rest.

> **Provisional — re-poker at `/start-phase`.**

| Task | Description | Points |
|------|-------------|--------|
| 3.1 | Weather poller + hypertable — poll the local JSON API, land readings idempotently. | ~5 |
| 3.2 | Weather + overview dashboards — weather beside soil/irrigation. | ~3 |

**Phase 3 coarse total: ~8 points (provisional).**

---

## Velocity Table

Updated at each phase boundary (throughput, DEC-S026).

| Phase | Date Closed | Points | Span (days) | Throughput (pts/wk) | Re-estimated | Net Drift | PRs |
|-------|-------------|--------|-------------|---------------------|--------------|-----------|-----|
| 0 | — | — | — | — | — | — | — |
| 1 | 2026-07-16 | 16 | 2 | burst — 16 pts in 2d | 0 | 0 | 5 |

---

## Phase Boundary Checklist

At the end of every phase:
1. Targeted tests green (ingest pytest; SQL smoke; end-to-end where relevant).
2. `/doc-consistency-check` if docs were touched heavily.
3. `/retro` — throughput velocity, mark `[x]`, write RETROSPECTIVES.md entry.
4. `/start-phase` for the next phase (materialize tasks as Issues).
