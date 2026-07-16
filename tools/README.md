# tools/ — dev / sim helpers

Not part of the running stack — local helpers for developing and proving the pipeline.

## `synth_publish.py` — synthetic tinkle publisher

Publishes v1 irrigation run-complete events to the broker the way real tinkle firmware will (see issue #13 for real-tinkle onboarding). Lets you prove the pipeline end-to-end without hardware.

```bash
.venv/bin/pip install paho-mqtt            # if not already in the venv
MQTT_HOST=localhost python tools/synth_publish.py            # publish a spread of runs
MQTT_HOST=localhost python tools/synth_publish.py --replay    # re-publish the same batch
```

Rows use `source = 'tinkle-sim'`, so simulated data is identifiable and easy to clear:

```sql
DELETE FROM irrigation_runs WHERE source = 'tinkle-sim';
```

The batch timestamps are truncated to the current hour, so `--replay` reproduces the same natural keys and the store dedups them — **run the replay in the same clock hour** as the original publish for the idempotency demo.

## End-to-end proof (task 1.5)

With the stack up (`docker compose -f deploy/docker-compose.yml up -d`):

```bash
# 1. run the daemon against the stack
MQTT_HOST=localhost PG_DSN=postgresql://poopdeck@localhost/farm \
    .venv/bin/python ingest/irrigation_ingest.py &

# 2. publish synthetic runs
MQTT_HOST=localhost python tools/synth_publish.py

# 3. confirm they landed
docker exec deploy-timescale-1 psql -U poopdeck -d farm \
    -c "SELECT count(*) FROM irrigation_runs WHERE source='tinkle-sim';"   # -> 6

# 4. replay proves idempotency — count stays 6
MQTT_HOST=localhost python tools/synth_publish.py --replay
```

The runs then render on the **Irrigation — tinkle** dashboard in Grafana (`:3000`).
