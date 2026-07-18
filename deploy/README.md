# deploy/ — the stack

`docker-compose.yml` brings up the whole pipeline:

- **Mosquitto** — the MQTT broker (`1883`), authenticated (per-producer creds + ACLs).
- **TimescaleDB** — the Postgres time-series store; `db/migrations/` applied on init. Reachable only on loopback + the compose network.
- **ingest** — the always-on irrigation daemon (built from `ingest/Dockerfile`), one per producer.
- **Grafana** — the dashboards (the only UI), real admin password, no anonymous access.

Pin every image. The compose stack runs the whole thing for development; the farm's headless box (bee-grace) runs the same shape.

## Secrets

All credentials live in `deploy/.env` (gitignored). Copy the template and fill it in **before** first `up`:

```bash
cp deploy/.env.example deploy/.env
# edit deploy/.env — set PG_PASSWORD, GRAFANA_ADMIN_PASSWORD, and the MQTT creds.
# keep PG_PASSWORD URL-safe (it goes into a DSN).
```

## Run it

Always pass `--env-file` so `${VARS}` resolve regardless of the directory you run from:

```bash
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d      # bring the stack up
docker compose --env-file deploy/.env -f deploy/docker-compose.yml down       # stop, keep data
docker compose --env-file deploy/.env -f deploy/docker-compose.yml down -v     # stop + wipe volumes
```

`up -d` builds the ingest image, starts the broker (generating its password file from the env creds), waits for Timescale to pass its healthcheck, then starts ingest and Grafana. `restart: unless-stopped` on every service means the stack comes back after a host reboot.

## What's exposed, and how it's locked down (#15)

- **TimescaleDB** — published on `127.0.0.1:5432` only, so host-local smoke checks work but the LAN can't reach it. Grafana + the daemon connect over the compose network (`timescale:5432`). The `poopdeck` role authenticates with a scram password on TCP; the container's local socket stays `trust`, so `docker compose exec timescale psql -U poopdeck` needs no password.
- **Mosquitto** — anonymous access is off. Each client authenticates; the ACL file (`mosquitto/aclfile`) confines `tinkle` to publishing `farm/irrigation/#` and lets `ingest` read `farm/#`. The password file is generated on the data volume at container start from the `MQTT_*` env vars — no credential artifact is committed.
- **Grafana** — real admin password from `GRAFANA_ADMIN_PASSWORD`; sign-up and anonymous access disabled.

**Still deliberately out of scope (kitchen-table LAN tier):** TLS on MQTT/Grafana, disk encryption, MFA, cert management. Those belong with internet exposure (#10), not here.

### Host firewall (ufw)

Confirm only the broker and Grafana are open to the LAN, plus Tailscale, default-deny inbound:

```bash
sudo ufw default deny incoming
sudo ufw allow in on tailscale0
sudo ufw allow 1883/tcp        # MQTT (LAN producers)
sudo ufw allow 3000/tcp        # Grafana (phones on the LAN)
sudo ufw status verbose        # 5432 must NOT appear — it's loopback-bound
```

## Upgrading an existing stack (bee-grace)

Both Postgres and Grafana bake credentials into their data volume on **first init only** — an existing volume ignores the new env passwords on restart.

**Grafana admin password.** `GF_SECURITY_ADMIN_PASSWORD` applies only when the `grafana-data` volume is first created; an existing volume keeps its old password (e.g. the Phase-1 `admin`/`admin`). Reset it in place:

```bash
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec grafana \
    grafana cli admin reset-admin-password "$GRAFANA_ADMIN_PASSWORD"
```

**Postgres auth.** `pg_hba.conf` is written **once, at first init**. A store first brought up under the old `trust` config keeps trust-auth TCP even after you pull these changes — restarting doesn't rewrite `pg_hba`. Two ways to actually apply the Postgres hardening:

- **Clean (recommended if the data is disposable):** `down -v` then `up`. This wipes the volumes and re-runs migrations on an empty store. The Phase-1 rows are synthetic (`source='tinkle-sim'`) — re-create them with `tools/synth_publish.py`.
- **Non-destructive:** keep the volume, set the role password over the local socket, then switch `pg_hba` to scram by hand:
  ```bash
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec timescale \
      psql -U poopdeck -d farm -c "ALTER ROLE poopdeck PASSWORD '<PG_PASSWORD>';"
  # then in the volume's pg_hba.conf: host ... trust → scram-sha-256, and reload.
  ```
  Use the clean path unless the store already holds data you can't reproduce.
