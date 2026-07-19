# deploy/ — the stack

`docker-compose.yml` brings up the whole pipeline:

- **Mosquitto** — the MQTT broker (`1883`), authenticated (per-producer creds + ACLs).
- **TimescaleDB** — the Postgres time-series store; `db/migrations/` applied on init. Reachable only on loopback + the compose network.
- **ingest** — the always-on irrigation daemon (built from `ingest/Dockerfile`), one per producer.
- **Grafana** — the dashboards (the only UI), real admin password, no anonymous access.

Pin every image. The compose stack runs the whole thing for development; the farm's headless box (bee-grace) runs the same shape.

## Getting to Grafana (the dashboards)

Grafana **is** the UI — everything you look at lives there. It listens on port **3000**.

| From | URL |
|------|-----|
| On bee-grace itself | `http://localhost:3000` |
| On the home LAN (phone, laptop) | `http://192.168.50.201:3000` — bee-grace's LAN address |
| Anywhere, over Tailscale | `http://100.105.112.4:3000` — bee-grace's Tailscale address |

Log in as **`admin`** with the password from `GRAFANA_ADMIN_PASSWORD` in `deploy/.env`. Sign-up and anonymous access are off, so there's no other way in. The irrigation dashboard is provisioned automatically — it's in the dashboards list once you're logged in.

(bee-grace's addresses can change — LAN IP if the router reassigns it, Tailscale IP is stable. `tailscale ip -4` and `ip -4 addr show wlo1` on the box print the current ones.)

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

### Host firewall (ufw) — deliberately NOT enabled

bee-grace does **not** run a host firewall, on purpose. The one thing that must not be LAN-reachable — the database — is already handled by the `127.0.0.1:5432` bind above, and the home LAN is a trusted zone (nothing else on it runs a host firewall either). A `ufw` layer on top of the loopback bind buys little and, on a headless box, adds a real lockout risk. So it's off.

**If you do want it** (e.g. the box moves to a less-trusted network), here is the *complete, safe* recipe — the important part is not locking yourself out of a box you can't walk up to:

```bash
# SSH FIRST, or you lose your only way in. Allow SSH from the LAN + Tailscale:
sudo ufw allow from 192.168.50.0/24 to any port 22 proto tcp   # LAN SSH fallback
sudo ufw allow in on tailscale0                                # Tailscale (SSH + all)
# Then the services:
sudo ufw allow 1883/tcp        # MQTT (LAN producers)
sudo ufw allow 3000/tcp        # Grafana (phones on the LAN)
sudo ufw default deny incoming # everything else inbound denied
sudo ufw enable                # <-- the rules do NOTHING until this runs
sudo ufw status verbose        # verify: 5432 must NOT appear (it's loopback-bound)
```

Order matters: add the SSH-allow rules **before** `enable`. Skip them and `default deny` will cut port 22 the moment you enable — and with a headless box, that means the only recovery is physical access or a reboot. Tailscale being your sole path is a single point of failure; the LAN SSH rule is the fallback for when Tailscale is down.

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
