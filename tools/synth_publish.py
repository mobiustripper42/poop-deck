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

Source is "tinkle-sim" so simulated rows are identifiable in the store:
    DELETE FROM irrigation_runs WHERE source = 'tinkle-sim';
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt

HOST = os.environ.get("MQTT_HOST", "localhost")
PORT = int(os.environ.get("MQTT_PORT", 1883))
SOURCE = os.environ.get("SYNTH_SOURCE", "tinkle-sim")


def batch(now):
    """A deterministic spread of runs over the last ~6 hours across two zones,
    including one faulted run. Deterministic ts_start so --replay produces the
    same natural keys (that's the whole point of the idempotency demo)."""
    base = now.replace(minute=0, second=0, microsecond=0)
    return [
        {"zone": 1, "ts_start": base - timedelta(hours=5), "duration_s": 600, "gallons": 12.4, "fertigated": False},
        {"zone": 2, "ts_start": base - timedelta(hours=5), "duration_s": 300, "gallons": 6.1,  "fertigated": False},
        {"zone": 1, "ts_start": base - timedelta(hours=3), "duration_s": 600, "gallons": 11.9, "fertigated": True},
        {"zone": 2, "ts_start": base - timedelta(hours=3), "duration_s": 300, "gallons": 5.8,  "fertigated": False},
        {"zone": 1, "ts_start": base - timedelta(hours=1), "duration_s": 600, "gallons": 12.1, "fertigated": False},
        {"zone": 2, "ts_start": base - timedelta(hours=1), "duration_s": 300, "gallons": 2.0,  "fertigated": False, "fault": "low-flow"},
    ]


def to_payload(run):
    p = {
        "v": 1,
        "source": SOURCE,
        "zone": run["zone"],
        "ts_start": run["ts_start"].astimezone(timezone.utc).isoformat(),
        "duration_s": run["duration_s"],
        "gallons": run["gallons"],
        "fertigated": run["fertigated"],
    }
    if run.get("fault"):
        p["fault"] = run["fault"]
    return p


def main():
    ap = argparse.ArgumentParser(description="Synthetic tinkle publisher")
    ap.add_argument("--replay", action="store_true",
                    help="re-publish the same batch (same natural keys) to demonstrate idempotency")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    runs = batch(now)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(HOST, PORT, keepalive=30)
    client.loop_start()

    for run in runs:
        payload = to_payload(run)
        topic = f"farm/irrigation/{SOURCE}/zone{run['zone']}"
        info = client.publish(topic, json.dumps(payload), qos=1)
        info.wait_for_publish()
        tag = f"  FAULT={payload['fault']}" if payload.get("fault") else ""
        print(f"{'replay' if args.replay else 'publish'} {topic}  zone {run['zone']}  {run['duration_s']}s  {run['gallons']} gal{tag}")

    time.sleep(0.5)  # let QoS-1 handshakes drain before disconnecting
    client.loop_stop()
    client.disconnect()
    print(f"{len(runs)} messages published to {HOST}:{PORT} (source={SOURCE})")


if __name__ == "__main__":
    main()
