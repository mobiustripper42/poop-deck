#!/usr/bin/env python3
"""
Poop Deck :: irrigation ingest daemon

Subscribes to farm/irrigation/+/+ and writes run-complete events to TimescaleDB.
Deliberately dumb. It validates, it inserts, it logs. Nothing else.

Receive and persist are decoupled by a bounded in-memory queue (DEC-006): the
MQTT callback only decodes + validates + enqueues, and a single worker thread
owns the DB connection and does all inserts + reconnect/backoff. That keeps the
blocking DB work off paho's network thread, so keepalive keeps flowing and the
MQTT session survives a DB outage instead of the broker dropping us mid-outage.

    pip install paho-mqtt psycopg[binary]
"""

import json
import logging
import os
import queue
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt
import psycopg

BROKER = os.environ.get("MQTT_HOST", "localhost")
PORT = int(os.environ.get("MQTT_PORT", 1883))
# Broker credentials (unset → anonymous, for local/dev brokers that allow it).
MQTT_USERNAME = os.environ.get("MQTT_USERNAME")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")
TOPIC = "farm/irrigation/+/+"
DSN = os.environ.get("PG_DSN", "postgresql://poopdeck@localhost/farm")
# Outage buffer: rows wait here while the DB is down. ~4k rows/year (SPEC), so
# 10k is years of headroom for tiny dicts. Full → drop-and-log (DEC-006).
QUEUE_MAX = int(os.environ.get("INGEST_QUEUE_MAX", 10_000))

REQUIRED = ("v", "source", "zone", "ts_start", "duration_s")
SCHEMA_V = 1

INSERT = """
INSERT INTO irrigation_runs
    (ts_start, source, zone, duration_s, gallons, fertigated, trigger, fault, schema_v)
VALUES
    (%(ts_start)s, %(source)s, %(zone)s, %(duration_s)s, %(gallons)s,
     %(fertigated)s, %(trigger)s, %(fault)s, %(v)s)
ON CONFLICT (source, zone, ts_start) DO NOTHING
"""

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("irrigation-ingest")


def build_row(payload, topic=""):
    """Validate a decoded payload and shape it into an insert row.

    Returns the row dict, or None to drop (missing fields / unknown schema
    version). Pure and side-effect-free apart from logging — the testable
    heart of the validate-and-drop contract (DEC-004).
    """
    # Valid JSON that isn't an object (null, a scalar, an array) would crash the
    # `k not in payload` check below — drop it, don't let a poison publish through.
    if not isinstance(payload, dict):
        log.warning("dropping %s, payload is not a JSON object: %r", topic, payload)
        return None

    missing = [k for k in REQUIRED if k not in payload]
    if missing:
        log.warning("dropping %s, missing fields: %s", topic, missing)
        return None

    if payload["v"] != SCHEMA_V:
        log.warning("unknown schema v=%s on %s, dropping", payload["v"], topic)
        return None

    return {
        "ts_start": payload["ts_start"],
        "source": payload["source"],
        "zone": payload["zone"],
        "duration_s": payload["duration_s"],
        "gallons": payload.get("gallons"),
        "fertigated": payload.get("fertigated", False),
        "trigger": payload.get("trigger"),
        "fault": payload.get("fault"),
        "v": payload["v"],
    }


def connect_db(dsn):
    """Open a DB connection, retrying with capped backoff until it succeeds.
    Runs on the worker thread only, so blocking here never stalls MQTT keepalive
    — the daemon waits an outage out instead of dying (see db_worker)."""
    delay = 1
    while True:
        try:
            return psycopg.connect(dsn, autocommit=False)
        except psycopg.OperationalError as e:
            log.error("db connect failed (%s); retrying in %ss", e, delay)
            time.sleep(delay)
            delay = min(delay * 2, 30)


def insert_row(conn, row):
    """Idempotently insert one row. A DB error rolls back and is logged — it
    never propagates, so a poison row can't kill the worker (DEC-004). Returns
    True on commit, False on a handled error (caller checks conn.closed to tell
    a poison row apart from a dropped connection)."""
    try:
        with conn.cursor() as cur:
            cur.execute(INSERT, row)
        conn.commit()
        log.info(
            "zone %s  %ss  %s gal  fert=%s%s",
            row["zone"],
            row["duration_s"],
            row["gallons"],
            row["fertigated"],
            f"  FAULT={row['fault']}" if row["fault"] else "",
        )
        return True
    except psycopg.Error as e:
        try:
            conn.rollback()
        except psycopg.Error:
            pass  # connection already gone — nothing to roll back
        log.error("insert failed: %s", e)
        return False


def persist(conn, row, dsn):
    """Insert one row, reconnecting once if the connection dropped mid-insert
    (a DB restart), and returning the connection to use for the next row. A
    poison row (conn still alive) is dropped-and-logged, not retried. This is
    the DB-side glue the worker loops over; pure enough to unit-test directly."""
    if conn is None or conn.closed:
        conn = connect_db(dsn)

    if not insert_row(conn, row) and conn.closed:
        # The connection died mid-insert (DB restart), not a poison row —
        # reconnect and replay this one message once. Idempotent insert makes
        # the replay safe even if the first attempt partially landed.
        conn = connect_db(dsn)
        insert_row(conn, row)
    return conn


def db_worker(q, dsn, stop):
    """Drain the queue to the DB forever. Owns the sole DB connection; all
    blocking (connect/backoff, insert) happens here, off the network thread.

    On `stop`, keep draining until the queue empties, then exit — so a graceful
    shutdown persists what was already buffered rather than dropping it. Any
    unexpected escape takes the whole process down (os._exit) so a dead worker
    can't leave a live process silently dropping every message; restart policy
    then recovers a healthy one. Loud failure over silent degradation."""
    try:
        conn = connect_db(dsn)
        while True:
            try:
                row = q.get(timeout=0.5)
            except queue.Empty:
                if stop.is_set():
                    break
                continue
            try:
                conn = persist(conn, row, dsn)
            finally:
                q.task_done()
        try:
            conn.close()
        except psycopg.Error:
            pass
    except BaseException:  # noqa: BLE001 — the backstop; must catch everything
        log.critical("ingest worker died — taking the process down", exc_info=True)
        os._exit(1)


def on_message(client, userdata, msg):
    """MQTT glue: decode → validate → enqueue. Cheap and non-blocking so paho's
    network thread is never held up; the worker does the DB work. Never raises."""
    try:
        payload = json.loads(msg.payload)
    except json.JSONDecodeError:
        log.warning("unparseable payload on %s: %r", msg.topic, msg.payload[:200])
        return

    row = build_row(payload, msg.topic)
    if row is None:
        return

    try:
        userdata["queue"].put_nowait(row)
    except queue.Full:
        # Bounded, logged loss (DEC-006) — the DB has been down long enough to
        # fill the buffer. Same contract as a dropped poison row: never silent.
        log.error("queue full (%s), dropping %s", userdata["queue"].maxsize, msg.topic)


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(TOPIC, qos=1)
        log.info("connected, subscribed to %s", TOPIC)
    else:
        log.error("connect failed rc=%s", rc)


def connect_broker(client, host, port, keepalive=60):
    """Connect to the broker, retrying with capped backoff — symmetric with
    connect_db, so a cold start before the broker is listening doesn't crash the
    daemon (self-contained; holds regardless of launcher, not just compose)."""
    delay = 1
    while True:
        try:
            client.connect(host, port, keepalive=keepalive)
            return
        except OSError as e:
            log.error("broker connect failed (%s); retrying in %ss", e, delay)
            time.sleep(delay)
            delay = min(delay * 2, 30)


def main():
    q = queue.Queue(maxsize=QUEUE_MAX)
    stop = threading.Event()
    worker = threading.Thread(target=db_worker, args=(q, DSN, stop), name="db-worker")
    worker.start()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        userdata={"queue": q},
    )
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    def bye(signum, frame):
        # Stop enqueuing first; the worker then drains the buffer below.
        log.info("shutting down")
        client.disconnect()

    signal.signal(signal.SIGTERM, bye)
    signal.signal(signal.SIGINT, bye)

    connect_broker(client, BROKER, PORT, keepalive=60)
    client.loop_forever()  # returns when bye() disconnects; auto-reconnects otherwise

    # Graceful drain: no more enqueues after disconnect, so let the worker finish
    # the backlog, then join. The timeout is a safety cap (e.g. DB down at exit),
    # not the primary path — docker's stop grace period would SIGKILL past it.
    stop.set()
    worker.join(timeout=30)
    sys.exit(0)


if __name__ == "__main__":
    main()
