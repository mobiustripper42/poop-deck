# dashboards/ — Grafana definitions Poop Deck owns

The **shared** Grafana instance lives with Poop Deck. This directory holds the dashboards Poop Deck itself owns — cross-producer / farm-overview views, and (Phase 1) the tinkle irrigation dashboard.

**A producer owns its own dashboard and alert *definitions* in its own repo** (e.g. soundings keeps its per-tunnel dashboards + alert rules as versioned config in the soundings repo), provisioned *into* this shared Grafana. Poop Deck hosts the instance; it does not absorb another producer's definitions (DEC-004, soundings-side). Phase 1 adds the irrigation dashboard; nothing here yet.
