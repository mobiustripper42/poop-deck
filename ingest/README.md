# ingest/ — one dumb daemon per producer

Each producer gets a small, always-on Python daemon that subscribes to its MQTT topic namespace and writes into its hypertable. Deliberately dumb: **validate → `INSERT … ON CONFLICT DO NOTHING` → log → drop anything malformed → never crash.** No derivation, ever — producers own their physics (DEC-001).

Dependencies: `paho-mqtt`, `psycopg[binary]`. Config via env (`MQTT_HOST`, `MQTT_PORT`, `PG_DSN`).

## Daemons

| File | Producer | Topic | Table | Status |
|------|----------|-------|-------|--------|
| `irrigation_ingest.py` | tinkle | `farm/irrigation/+/+` | `irrigation_runs` | Wired against the compose stack. `build_row` validates, `insert_row` writes idempotently, `on_message` glues them. |

## Run it

```bash
MQTT_HOST=localhost PG_DSN=postgresql://poopdeck@localhost/farm \
    python ingest/irrigation_ingest.py
```

## Tests

```bash
python3 -m venv .venv && .venv/bin/pip install pytest paho-mqtt 'psycopg[binary]'
.venv/bin/python -m pytest                 # unit tests only (fake DB seam, no services)
PG_DSN=postgresql://poopdeck@localhost/farm .venv/bin/python -m pytest   # + live redelivery no-op
```

Unit tests use a fake DB seam, so they run without a broker or database. The one live test (`test_redelivery_is_a_noop_live`) inserts the same row twice against the running stack and asserts one row survives; it **skips** cleanly if no Timescale is reachable.

## The contract every daemon honors (DEC-004)

- **Topic namespace per producer** — `farm/<producer>/…`.
- **JSON, schema-versioned with `v`** — unknown `v` is dropped, never best-effort parsed.
- **Natural-key idempotency** — a redelivered message is a no-op, not a double-count.
- **Validate-and-drop** — required fields missing / bad JSON → log at WARNING and drop. A DB error rolls back and the daemon keeps going. A poison message must never kill the loop.
