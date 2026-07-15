# deploy/ — the stack

**Phase 1 lands a `docker-compose.yml` here** bringing up the three pieces the pipeline runs on:

- **Mosquitto** — the MQTT broker (`1883`).
- **TimescaleDB** — the Postgres time-series store; `db/migrations/` applied on init.
- **Grafana** — the dashboards (the only UI). Producer dashboards provision in from each producer's repo; shared/overview dashboards live in `dashboards/`.

Pin every image. The compose stack runs the whole thing on a laptop for development; the real deployment mirrors its shape on the farm's headless box (the Beelink).

```bash
docker compose -f deploy/docker-compose.yml up -d      # bring the stack up
docker compose -f deploy/docker-compose.yml down       # stop, keep data
docker compose -f deploy/docker-compose.yml down -v     # stop + wipe volumes
```

- **TimescaleDB** on `5432` — user `poopdeck`, db `farm` (matches the daemon DSN `postgresql://poopdeck@localhost/farm`). `db/migrations/` is mounted into `/docker-entrypoint-initdb.d` and replays **in filename order on first init only** — an empty data volume. To re-apply from scratch, `down -v` then `up`.
- **Mosquitto** on `1883` — anonymous listener for local dev (`mosquitto/mosquitto.conf`).
- **Grafana** on `3000` — data-only for now; dashboard/datasource provisioning lands in task 1.4.
