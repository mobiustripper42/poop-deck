# db/ — schema ledger

Ordered SQL migrations applied to the TimescaleDB store. Migrations are the source of truth — never edit an applied migration, never patch schema through a dashboard (`CLAUDE.md § Migration Protocol`). Apply in filename order; a new hypertable ships with its natural-key unique index **in the same file**.

## Migrations

| File | Producer | Notes |
|------|----------|-------|
| `migrations/0000_enable_timescaledb.sql` | — | Enables the TimescaleDB extension. Sorts first so every hypertable migration can call `create_hypertable()`. Cross-producer, not irrigation-specific. |
| `migrations/0001_irrigation_runs.sql` | tinkle | Semantic-only hypertable (`gallons`, `duration_s`): correct for an *event* producer, where the run's fields *are* the fact. Natural key `(source, zone, ts_start)`, `ON CONFLICT DO NOTHING` for QoS-1 redelivery. |

## Smoke checks

`smoke/*.sql` — re-runnable, side-effect-free (wrapped in a transaction that `ROLLBACK`s) checks that a migration's schema behaves. Run against the compose stack:

```bash
docker exec -i deploy-timescale-1 psql -U poopdeck -d farm \
    -v ON_ERROR_STOP=1 -f - < db/smoke/irrigation_runs_smoke.sql
```

`irrigation_runs_smoke.sql` asserts: it's a hypertable, the natural-key unique index exists, a duplicate insert is a no-op, and the gallons/min query runs. Exits non-zero on any failed assertion.

## Storage-kind rule (DEC-005)

- **Event producers** (tinkle) → **semantic** columns. A valve-open *is* the fact.
- **Sensor producers** (soundings) → **raw + derived** columns. Raw resistance / T-RH is the ground truth and the durable record; kPa/VPD are a re-revisable lens stored alongside for convenience. **Do not** copy the semantic-only irrigation schema for `soundings_readings` — it must carry raw per-channel counts *and* derived columns, keyed on `(node_id, seq)`.

Retention: keep raw forever. Events and readings are tiny (an irrigation run every 15 min is ~4k rows/year); no downsampling needed.
