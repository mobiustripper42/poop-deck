# deploy/ — the stack

**Phase 1 lands a `docker-compose.yml` here** bringing up the three pieces the pipeline runs on:

- **Mosquitto** — the MQTT broker (`1883`).
- **TimescaleDB** — the Postgres time-series store; `db/migrations/` applied on init.
- **Grafana** — the dashboards (the only UI). Producer dashboards provision in from each producer's repo; shared/overview dashboards live in `dashboards/`.

Pin every image. The compose stack runs the whole thing on a laptop for development; the real deployment mirrors its shape on the farm's headless box (the Beelink). Nothing to run yet — placeholder until task 1.1.
