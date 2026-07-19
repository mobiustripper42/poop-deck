---
session: 4
dev: eric
slug: harden-and-service
branch: task/harden-and-service
started: 2026-07-18T14:14:48Z
ended:
points:
pr_numbers: [23, 24]
status: open
transcript: /home/estoffer/.claude/projects/-home-estoffer-poop-deck/d4b4d6fa-3757-4924-b2ff-0ef8f1100a46.jsonl
---

# Session 4 — harden-and-service

<!-- Task blocks appended by /kill-this, one per task. -->

## Task 1: Ingest reconnect — decouple receive from persist via a bounded worker queue (#21)

**Completed:**
- Reworked `ingest/irrigation_ingest.py`: `on_message` now decodes + `build_row` validate-and-drop + `put_nowait` onto a bounded `queue.Queue`, never touching the DB. A single `db_worker` thread owns the connection and does all inserts + reconnect/backoff. Fixes the silent-loss bug: `connect_db` no longer blocks paho's network thread, so keepalive keeps flowing and the broker doesn't drop the clean-session client (~90s) during a DB outage.
- `persist` helper (reconnect-once-on-drop vs poison-row-drop, relocated off the network thread). Queue-full → drop-and-log (DEC-006). Graceful shutdown drains the queue; an unexpected worker death → `os._exit` so `restart:unless-stopped` recovers. `connect_broker` wraps the initial connect with retry and observes `stop` (review fix).
- Tests adapted to the worker model: enqueue paths, `persist` reconnect cases, worker drain + in-flight-drain. **28 pass, 1 skipped** (live-DB test).
- `docs/DECISIONS.md`: DEC-006 (bounded-queue decouple, @architect-blessed), DEC-007 (shared `ingest` ACL credential).
- **Verified live on bee-grace:** 100s DB outage past the keepalive window — MQTT session survived (only the synth publisher's own clients disconnected), messages buffered, worker drained on DB recovery, replays deduped (rows 6→12). ~30s recovery lag = the capped backoff, acceptable.

**Also this session (pre-#21):** upgraded bee-grace's live stack to the hardened config (clean `down -v` + re-init; pg_hba now scram, Grafana real admin password, synthetic rows re-seeded). Operational, no PR. Decided **against** enabling ufw (LAN is trusted, DB already loopback-bound). README doc updates (Grafana access + ufw) staged for a separate PR.

**Code review:** @code-review — 1 real finding (connect_broker ignored shutdown signals → hang-to-SIGKILL on cold-start SIGTERM), fixed; 1 test-coverage add (stop-while-mid-persist), added. Core decoupling confirmed sound — contract/idempotency intact, no computation added.
**PR:** [#23](https://github.com/mobiustripper42/poop-deck/pull/23)
**Points:** 5
**Branch:** task/21-ingest-worker-queue
**Opened at:** 2026-07-19T03:12:42Z

## Task 2: deploy docs — Grafana access + honest ufw section

**Completed:**
- `deploy/README.md`: added a "Getting to Grafana" table near the top (LAN `192.168.50.201` + Tailscale `100.105.112.4`, port 3000, `admin` + `deploy/.env` password).
- Rewrote the ufw section: bee-grace deliberately does **not** run a host firewall (LAN trusted, DB already loopback-bound). The old block was also unsafe (no `enable`, no SSH-allow → would lock out a headless box); replaced with a complete, lockout-safe recipe (SSH allow for LAN subnet + Tailscale, then enable) for if ever wanted.

**Code review:** Docs-only (markdown) — no review agent run.
**PR:** [#24](https://github.com/mobiustripper42/poop-deck/pull/24)
**Points:** 1
**Branch:** task/deploy-docs-grafana-ufw
**Opened at:** 2026-07-19T03:14:11Z

**Next Steps:**

**Context:**
