#!/usr/bin/env python3
"""
Poop Deck :: irrigation ingest daemon

Subscribes to farm/irrigation/+/+ and writes run-complete events to TimescaleDB.
Deliberately dumb. It validates, it inserts, it logs. Nothing else.

    pip install paho-mqtt psycopg[binary]
"""

import json
import logging
import os
import signal
import sys

import paho.mqtt.client as mqtt
import psycopg

BROKER = os.environ.get("MQTT_HOST", "localhost")
PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC = "farm/irrigation/+/+"
DSN = os.environ.get("PG_DSN", "postgresql://poopdeck@localhost/farm")

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


def insert_row(conn, row):
    """Idempotently insert one row. A DB error rolls back and is logged —
    it never propagates, so a poison row can't kill the daemon (DEC-004)."""
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
    except psycopg.Error as e:
        conn.rollback()
        log.error("insert failed: %s", e)


def on_message(client, userdata, msg):
    """MQTT glue: decode → validate → insert. Never raises out of here."""
    try:
        payload = json.loads(msg.payload)
    except json.JSONDecodeError:
        log.warning("unparseable payload on %s: %r", msg.topic, msg.payload[:200])
        return

    row = build_row(payload, msg.topic)
    if row is None:
        return

    insert_row(userdata["conn"], row)


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(TOPIC, qos=1)
        log.info("connected, subscribed to %s", TOPIC)
    else:
        log.error("connect failed rc=%s", rc)


def main():
    conn = psycopg.connect(DSN, autocommit=False)
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, userdata={"conn": conn}
    )
    client.on_connect = on_connect
    client.on_message = on_message

    def bye(signum, frame):
        log.info("shutting down")
        client.disconnect()
        conn.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, bye)
    signal.signal(signal.SIGINT, bye)

    client.connect(BROKER, PORT, keepalive=60)
    client.loop_forever()  # auto-reconnects


if __name__ == "__main__":
    main()
