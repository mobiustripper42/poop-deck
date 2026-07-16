# dashboards/ — Grafana definitions Poop Deck owns

The **shared** Grafana instance lives with Poop Deck. This directory holds the dashboards Poop Deck itself owns — cross-producer / farm-overview views, and (Phase 1) the tinkle irrigation dashboard.

**A producer owns its own dashboard and alert *definitions* in its own repo** (e.g. soundings keeps its per-tunnel dashboards + alert rules as versioned config in the soundings repo), provisioned *into* this shared Grafana. Poop Deck hosts the instance; it does not absorb another producer's definitions (DEC-004, soundings-side).

## Layout

```
provisioning/
  datasources/timescaledb.yml   TimescaleDB datasource (uid poopdeck-timescale)
  dashboards/poopdeck.yml        file provider → reads /etc/dashboards
tinkle/
  irrigation.json                the tinkle irrigation dashboard
```

The compose Grafana bind-mounts `provisioning/datasources` and `provisioning/dashboards` into `/etc/grafana/provisioning/…` (the specific subdirs, so Grafana's own `plugins/` + `alerting/` stay intact), and `tinkle/` into `/etc/dashboards/tinkle`. Everything provisions on boot — no clicking.

**Irrigation dashboard** (`tinkle/irrigation.json`): single-column, phone-usable. Panels — faults-in-range stat (red on any fault), gallons/min by zone, run history, and a faults table. All time-range-scoped off `ts_start`. Grafana is reachable at `:3000` (default `admin`/`admin` until prod-hardening — see `deploy/README.md` and issue #10).
