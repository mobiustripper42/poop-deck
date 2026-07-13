# Poop Deck — Architectural Decisions

Decisions are numbered DEC-NNN. "DEC-TBD" means a decision is flagged but unresolved — consult @architect before building. This file is reserved for decisions whose *reasoning* is worth preserving; smaller settled choices live in `SPEC.md`.

---

## DEC-001: Poop Deck is a dumb store — it never computes

**Decision:** Poop Deck validates a payload, writes it, logs it, and drops anything malformed. That is the whole job. It does **not** derive, convert, roll up, or interpret. Producers own their own physics and derivation (kPa, VPD, gallons, tension curves); Poop Deck stores what they send and never recomputes it.

**Why:**
- **One responsibility, one failure domain.** A store that only stores is a store that rarely surprises you. This is an unattended, always-on backend on a headless farm box — boring is the point.
- **Derivation stays re-revisable at the producer.** If a calibration curve changes, the producer re-derives and republishes; the store didn't bake a stale equation into its ingest path.
- **No hidden coupling.** The moment the store computes something, it owns a piece of a producer's domain and every producer's change can break ingest.

**Tradeoff:** Derivation logic can be duplicated across producers, and the store can't "fix" a producer's bad math after the fact — a wrong derived value is stored as sent (which is why sensor producers also store raw; see DEC-005). Accepted: the store's simplicity is worth more than DRY across repos.

**Revisit:** Not foreseen. If a genuinely store-side concern appears (e.g. continuous aggregates for retention/rollup), it's a *storage* optimization, not producer physics — bring it to @architect framed that way.

---

## DEC-002: One-way, per-producer boundary

**Decision:** Each producer publishes into its **own** topic namespace (`farm/<producer>/…`) and its **own** hypertable. No producer consumes another producer's data directly — not as a repo dependency, not as a cross-table read in an ingest daemon. Cross-links (e.g. tinkle wanting soundings' tank level for a pump lockout) happen **through** Poop Deck as a query against the shared store, never as a direct link between producer repos.

**Why:**
- **Autonomy.** A producer keeps working when Poop Deck is dark — a Poop Deck outage is a *dropped publish*, nothing worse. Nothing in the field waits on the store.
- **Blast-radius containment.** One producer's schema or topic change can't reach into another's ingest path.
- **The farm is a mesh of independent devices, not a distributed system.** Keep the seams one-way.

**Tradeoff:** A consumer that wants another producer's data pays a query against the store (and tolerates its staleness/absence) rather than getting a live feed. That's the correct cost — it keeps the coupling loose and legible.

**Revisit:** If a real-time cross-producer need appears that a store query genuinely can't serve. Not V1.

---

## DEC-003: TimescaleDB / Postgres is the store (soundings D6 counterparty)

**Decision:** The store is **TimescaleDB** (a PostgreSQL extension) — hypertables for the time-series data, plain Postgres for everything relational. Not VictoriaMetrics, not InfluxDB, not a bare metrics TSDB.

**Why:**
- **Real SQL JOINs to farm records.** The reason a farm telemetry store earns a relational engine is correlating sensor/event data against the farm's other records (yield, fertigation, journal). That's a Postgres counterparty, and Poop Deck *is* it.
- **One store, farm-wide.** tinkle already writes here; soundings and weather join the same engine, so cross-producer analysis is a JOIN, not an ETL.
- **Grafana-native.** Postgres is a first-class Grafana datasource with alerting.

**Tradeoff:** More operational surface than a single-binary metrics store (VictoriaMetrics' one-flag retention was the tempting alternative). Accepted because the JOIN-to-farm-records requirement is real and only a SQL store serves it — and the store runs on a proper headless box, not a RAM-constrained Pi, so the VM edge shrinks. **This resolves soundings' deferred decision D6** (soundings retires its provisional VictoriaMetrics + Grafana; storage and graphing move here).

**Revisit:** If the ops burden proves real and the JOIN requirement evaporates — not expected.

---

## DEC-004: The ingest contract — JSON over MQTT, `v`-versioned, idempotent, validate-and-drop

**Decision:** Every producer talks to Poop Deck the same way:
- **Transport:** JSON payloads over MQTT, published to `farm/<producer>/…`.
- **Versioned:** every payload carries a `v` schema-version integer. An unknown `v` is **dropped**, never best-effort parsed.
- **Idempotent:** each hypertable declares a **natural key** and ingest is `INSERT … ON CONFLICT (natural key) DO NOTHING`. A QoS redelivery or a replayed backfill is a no-op, never a double-count.
- **Validate-and-drop, never-crash:** required fields missing or JSON unparseable → log at WARNING and drop the message. A DB error rolls back and the daemon keeps running. A poison message must never kill the loop.

**Why:** These four properties are what let the store be dumb *and* trustworthy. MQTT QoS can redeliver; nodes can replay backfill; producers can send garbage during a firmware bug — and none of it corrupts the store or takes it down.

**Tradeoff:** JSON on the wire (not a compact binary) — fine, this is a LAN broker, not the radio link. The natural key must be chosen correctly per producer or dedup silently fails; that choice is an onboarding decision (@architect).

**Revisit:** A `v` bump is how a producer's payload schema evolves — additive fields need no bump; a layout-incompatible change does. The contract itself is stable.

---

## DEC-005: Storage shape is producer-kind-specific — semantic for events, raw+derived for sensors

**Decision:** How a producer's data is stored depends on what kind of producer it is:
- **Event producers** (tinkle) → **semantic columns only.** An irrigation run's `gallons` / `duration_s` *are* the fact; there's no lower "raw" truth beneath them. `irrigation_runs` is semantic-only and that is correct.
- **Sensor producers** (soundings) → **raw AND derived columns.** Raw per-channel counts (resistance, T/RH ticks) are the ground truth and the durable record; derived values (kPa, VPD, gallons) are a re-revisable lens stored alongside for query convenience. The gateway derives and publishes **both**; the hypertable stores **both**.

**Why:** For a sensor, the derived value is a *lens* over raw physics and calibration curves get re-fit — so raw must be preserved to re-derive later without reflashing or re-collecting. For an event, there is no raw beneath the semantic fact, so storing "raw" would be inventing a layer. **Copying the semantic-only irrigation schema onto `soundings_readings` would regress the soundings pipeline** (its gateway already puts raw on the wire) and throw away the re-revisability that raw preservation exists to protect.

**Natural keys differ by producer:** `(source, zone, ts_start)` for tinkle events; `(node_id, seq)` — or `(node_id, channel, received_at)` — for soundings readings.

**Tradeoff:** Sensor tables are wider (raw + derived) and carry redundant-looking columns. Accepted: the raw columns are the point; storage is cheap and readings are tiny.

**Revisit:** Per new producer, at onboarding — decide event vs sensor and pick the natural key with @architect.

---

*Settled operational choices (keep raw forever / no downsampling; pin every container image; Mosquitto as the broker; Grafana as the only UI) live as prose in `SPEC.md`. They graduate to a DEC here only if their reasoning needs preserving.*
