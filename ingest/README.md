# ingest/ — one dumb daemon per producer

Each producer gets a small, always-on Python daemon that subscribes to its MQTT topic namespace and writes into its hypertable. Deliberately dumb: **validate → `INSERT … ON CONFLICT DO NOTHING` → log → drop anything malformed → never crash.** No derivation, ever — producers own their physics (DEC-001).

Dependencies: `paho-mqtt`, `psycopg[binary]`. Config via env (`MQTT_HOST`, `MQTT_PORT`, `PG_DSN`).

## Daemons

| File | Producer | Topic | Table | Status |
|------|----------|-------|-------|--------|
| `irrigation_ingest.py` | tinkle | `farm/irrigation/+/+` | `irrigation_runs` | **Staged from the tinkle handoff — Phase-1 substrate.** Wired against the compose stack in Phase 1. |

## The contract every daemon honors (DEC-004)

- **Topic namespace per producer** — `farm/<producer>/…`.
- **JSON, schema-versioned with `v`** — unknown `v` is dropped, never best-effort parsed.
- **Natural-key idempotency** — a redelivered message is a no-op, not a double-count.
- **Validate-and-drop** — required fields missing / bad JSON → log at WARNING and drop. A DB error rolls back and the daemon keeps going. A poison message must never kill the loop.
