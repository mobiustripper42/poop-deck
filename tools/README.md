# tools/ — dev / sim helpers

Not part of the running stack — local helpers for developing and proving the pipeline.

## `synth_publish.py` — synthetic tinkle publisher

Publishes v1 irrigation run-complete events to the broker the way real tinkle firmware will (see issue #13 for real-tinkle onboarding). Lets you prove the pipeline end-to-end without hardware.

Against the hardened broker, pass the `tinkle` producer credentials (from `deploy/.env`):

```bash
.venv/bin/pip install paho-mqtt            # if not already in the venv
export MQTT_HOST=localhost MQTT_USERNAME=tinkle MQTT_PASSWORD=...   # tinkle creds
python tools/synth_publish.py            # publish a spread of runs
python tools/synth_publish.py --replay    # re-publish the same batch
```

Rows use `source = 'tinkle-sim'`, so simulated data is identifiable and easy to clear:

```sql
DELETE FROM irrigation_runs WHERE source = 'tinkle-sim';
```

`--replay` resends the exact payloads saved from the last plain run (to a temp file), so the natural keys match and the store dedups them no matter when you replay. Run a plain publish once before `--replay`.

## End-to-end proof (task 1.5)

The ingest daemon now runs inside the stack (the `ingest` service), so you don't start it by hand — bring the stack up and publish:

```bash
# 0. stack up (daemon included)
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d

# 1. publish synthetic runs as the tinkle producer
export MQTT_HOST=localhost MQTT_USERNAME=tinkle MQTT_PASSWORD=...
python tools/synth_publish.py

# 2. confirm they landed (docker exec uses the container's trust socket — no PG password)
docker exec deploy-timescale-1 psql -U poopdeck -d farm \
    -c "SELECT count(*) FROM irrigation_runs WHERE source='tinkle-sim';"   # -> 6

# 3. replay proves idempotency — count stays 6
python tools/synth_publish.py --replay

# watch the daemon do its work
docker compose --env-file deploy/.env -f deploy/docker-compose.yml logs -f ingest
```

The runs then render on the **Irrigation — tinkle** dashboard in Grafana (`:3000`).
