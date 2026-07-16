#!/usr/bin/env python3
"""
Poop Deck :: synthetic tinkle publisher (dev / sim)

Publishes v1 irrigation run-complete events to the broker, the way real tinkle
firmware will. Used to prove the pipeline end-to-end (publish -> daemon ->
Timescale -> dashboard) without hardware, and to demonstrate that a replayed
message is a no-op.

    pip install paho-mqtt

    # publish a spread of runs across zones (one faulted)
    MQTT_HOST=localhost python tools/synth_publish.py

    # re-publish the exact same batch to prove idempotency (redelivery no-op)
    MQTT_HOST=localhost python tools/synth_publish.py --replay

--replay resends the payloads saved from the last plain run (see STATE_FILE), so
the natural keys match exactly regardless of when you replay. Source is
"tinkle-sim" so simulated rows are identifiable in the store:
    DELETE FROM irrigation_runs WHERE source = 'tinkle-sim';
"""

import argparse
import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt

HOST = os.environ.get("MQTT_HOST", "localhost")
PORT = int(os.environ.get("MQTT_PORT", 1883))
SOURCE = os.environ.get("SYNTH_SOURCE", "tinkle-sim")
# Rendered payloads from the last plain run, so --replay resends them verbatim.
STATE_FILE = os.path.join(tempfile.gettempdir(), "poopdeck_synth_batch.json")


def batch(now: datetime) -> list[dict]:
    """A deterministic spread of runs over the last ~6 hours across two zones,
    including one faulted run."""
    base = now.replace(minute=0, second=0, microsecond=0)
    return [
        {"zone": 1, "ts_start": base - timedelta(hours=5), "duration_s": 600, "gallons": 12.4, "fertigated": False},
        {"zone": 2, "ts_start": base - timedelta(hours=5), "duration_s": 300, "gallons": 6.1,  "fertigated": False},
        {"zone": 1, "ts_start": base - timedelta(hours=3), "duration_s": 600, "gallons": 11.9, "fertigated": True},
        {"zone": 2, "ts_start": base - timedelta(hours=3), "duration_s": 300, "gallons": 5.8,  "fertigated": False},
        {"zone": 1, "ts_start": base - timedelta(hours=1), "duration_s": 600, "gallons": 12.1, "fertigated": False},
        {"zone": 2, "ts_start": base - timedelta(hours=1), "duration_s": 300, "gallons": 2.0,  "fertigated": False, "fault": "low-flow"},
    ]


def to_payload(run: dict) -> dict:
    payload = {
        "v": 1,
        "source": SOURCE,
        "zone": run["zone"],
        "ts_start": run["ts_start"].astimezone(timezone.utc).isoformat(),
        "duration_s": run["duration_s"],
        "gallons": run["gallons"],
        "fertigated": run["fertigated"],
    }
    if run.get("fault"):
        payload["fault"] = run["fault"]
    return payload


def resolve_payloads(replay: bool) -> list[dict]:
    """Build a fresh batch (and save it) on a plain run; reload the saved
    payloads verbatim on --replay so the natural keys match exactly."""
    if replay:
        if not os.path.exists(STATE_FILE):
            raise SystemExit(f"--replay: no prior batch at {STATE_FILE}; run once without --replay first")
        with open(STATE_FILE) as f:
            return json.load(f)

    payloads = [to_payload(run) for run in batch(datetime.now(timezone.utc))]
    with open(STATE_FILE, "w") as f:
        json.dump(payloads, f)
    return payloads


def connected_client() -> mqtt.Client:
    """Connect and block until the broker acks (CONNACK), so we never publish
    into a not-yet-connected client."""
    ready = threading.Event()

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            ready.set()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.connect(HOST, PORT, keepalive=30)
    client.loop_start()
    if not ready.wait(timeout=10):
        client.loop_stop()
        raise SystemExit(f"could not connect to broker {HOST}:{PORT} within 10s")
    return client


def main() -> None:
    ap = argparse.ArgumentParser(description="Synthetic tinkle publisher")
    ap.add_argument("--replay", action="store_true",
                    help="re-publish the exact payloads from the last run (same natural keys) to demonstrate idempotency")
    args = ap.parse_args()

    payloads = resolve_payloads(args.replay)
    client = connected_client()

    for payload in payloads:
        topic = f"farm/irrigation/{payload['source']}/zone{payload['zone']}"
        info = client.publish(topic, json.dumps(payload), qos=1)
        info.wait_for_publish()
        tag = f"  FAULT={payload['fault']}" if payload.get("fault") else ""
        print(f"{'replay' if args.replay else 'publish'} {topic}  zone {payload['zone']}  {payload['duration_s']}s  {payload['gallons']} gal{tag}")

    time.sleep(0.5)  # let QoS-1 handshakes drain before disconnecting
    client.loop_stop()
    client.disconnect()
    print(f"{len(payloads)} messages published to {HOST}:{PORT} (source={SOURCE})")


if __name__ == "__main__":
    main()
