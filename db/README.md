# db/ — schema ledger

Ordered SQL migrations applied to the TimescaleDB store. Migrations are the source of truth — never edit an applied migration, never patch schema through a dashboard (`CLAUDE.md § Migration Protocol`). Apply in filename order; a new hypertable ships with its natural-key unique index **in the same file**.

## Migrations

| File | Producer | Notes |
|------|----------|-------|
| `migrations/0001_irrigation_runs.sql` | tinkle | **Staged from the tinkle handoff — Phase-1 substrate, not yet applied.** Semantic-only hypertable (`gallons`, `duration_s`): correct for an *event* producer, where the run's fields *are* the fact. Natural key `(source, zone, ts_start)`, `ON CONFLICT DO NOTHING` for QoS-1 redelivery. |

## Storage-kind rule (DEC-005)

- **Event producers** (tinkle) → **semantic** columns. A valve-open *is* the fact.
- **Sensor producers** (soundings) → **raw + derived** columns. Raw resistance / T-RH is the ground truth and the durable record; kPa/VPD are a re-revisable lens stored alongside for convenience. **Do not** copy the semantic-only irrigation schema for `soundings_readings` — it must carry raw per-channel counts *and* derived columns, keyed on `(node_id, seq)`.

Retention: keep raw forever. Events and readings are tiny (an irrigation run every 15 min is ~4k rows/year); no downsampling needed.
