# ingest/ — one dumb daemon per producer

Each producer gets a small, always-on Python daemon that subscribes to its MQTT topic namespace and writes into its hypertable. Deliberately dumb: **validate → `INSERT … ON CONFLICT DO NOTHING` → log → drop anything malformed → never crash.** No derivation, ever — producers own their physics (DEC-001).

Dependencies: `paho-mqtt`, `psycopg[binary]`. Config via env: `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `PG_DSN`. Broker creds are optional — unset means anonymous (dev brokers only).

## Daemons

| File | Producer | Topic | Table | Status |
|------|----------|-------|-------|--------|
| `irrigation_ingest.py` | tinkle | `farm/irrigation/+/+` | `irrigation_runs` | Runs as the `ingest` service in the compose stack (`Dockerfile`), `restart: unless-stopped`. `build_row` validates, `insert_row` writes idempotently, `on_message` glues them and reconnects on a dropped DB connection. |

## Always-on service (#14)

In the stack the daemon runs from `Dockerfile` as the `ingest` service — `depends_on` a healthy Timescale + the broker, `restart: unless-stopped`, so it survives a host reboot. Inside compose it connects to the service names (`mosquitto:1883`, `timescale:5432`), not `localhost`.

Two failure modes are handled so the container never wedges:
- **Broker blip** — paho's `loop_forever()` auto-reconnects.
- **DB blip / restart** — `connect_db` retries with capped backoff at startup, and `on_message` reconnects and replays the message if the connection drops mid-insert. (A poison-row error still just rolls back and drops — that's not a connection loss.)

## Run it standalone

```bash
# dev broker (anonymous), passwordless local PG
MQTT_HOST=localhost PG_DSN=postgresql://poopdeck@localhost/farm \
    python ingest/irrigation_ingest.py

# against the hardened stack from the host
MQTT_HOST=localhost MQTT_USERNAME=ingest MQTT_PASSWORD=... \
    PG_DSN=postgresql://poopdeck:PASS@localhost/farm \
    python ingest/irrigation_ingest.py
```

## Tests

```bash
python3 -m venv .venv && .venv/bin/pip install pytest paho-mqtt 'psycopg[binary]'
.venv/bin/python -m pytest                 # unit tests only (fake DB seam, no services)
# + live redelivery no-op (needs the password against the hardened stack):
PG_DSN=postgresql://poopdeck:PASS@localhost/farm .venv/bin/python -m pytest
```

Unit tests use a fake DB seam, so they run without a broker or database — this includes the DB-reconnect path (a fake connection that "dies" mid-insert). The one live test (`test_redelivery_is_a_noop_live`) inserts the same row twice against the running stack and asserts one row survives; it **skips** cleanly if no Timescale is reachable (including when the DSN lacks the now-required password).

## The contract every daemon honors (DEC-004)

- **Topic namespace per producer** — `farm/<producer>/…`.
- **JSON, schema-versioned with `v`** — unknown `v` is dropped, never best-effort parsed.
- **Natural-key idempotency** — a redelivered message is a no-op, not a double-count.
- **Validate-and-drop** — required fields missing / bad JSON → log at WARNING and drop. A DB error rolls back and the daemon keeps going. A poison message must never kill the loop.
