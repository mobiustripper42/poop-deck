# poop-deck — Retrospectives

Phase-end retrospectives, written by `/retro` at each phase boundary. Newest first.

Velocity is tracked as **throughput (points per calendar week)** at phase boundaries (DEC-S026), not hours/point.

<!-- /retro prepends entries below this line -->

## Phase 1 — 2026-07-16

**Points:** 16 / 16 (100%)
**Span:** 2 days (2026-07-14 21:32 → 2026-07-16 21:41)
**Throughput:** burst — 16 pts in 2d (sub-week phase; no per-week rate quoted, DEC-S026)
**Estimate calibration:** 0 tasks re-estimated, net drift 0 pts — every task shipped at its original points
**Sessions:** 1   **PRs merged:** 5
**Issues:** 5 created, 5 closed, 0 moved

### Phase throughput line
| Phase | Date | Points | Span(d) | Throughput | Re-est'd | Net drift | Sessions | PRs |
|-------|------|--------|---------|------------|----------|-----------|----------|-----|
| 1 | 2026-07-16 | 16 | 2 | burst — 16 pts in 2d | 0 | 0 | 1 | 5 |

### Notes
Retro notes and PM commentary skipped by request. The thinnest real slice landed end to end: MQTT publish → dumb daemon → TimescaleDB → Grafana dashboard, with idempotent replay proven. Every code-review pass caught something worth fixing before merge — most notably a pre-existing never-crash gap in the daemon (non-object JSON, 1.3) and a publish-before-CONNACK race in the sim tool (1.5). Friction this phase was environmental (Docker install, docker-group access, hostname resolution from phones, review agents tearing the stack down), not in the code.

### Scope changes
- Phase 0 (scaffold) was never formally retro'd — carried straight into Phase 1.
- Backlog filed during the phase (not scheduled): #10 remote access, #11 control tinkle (`needs-decision`, reverses DEC-002), #13 real-tinkle firmware onboarding, #14 always-on ingest daemon, #15 proportionate bee-grace hardening.
