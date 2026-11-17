#!/usr/bin/env python3
"""
Part A - step 7: alert subscriber.
Subscribes to the WILDCARD topic factory/+/temperature at QoS 1 and prints an ALERT line only
when the value exceeds THRESHOLD (default 90.0).

Extra (so that the 'LWT is received by both subscribers' observation holds) it also listens to
factory/+/status and prints a one-line notice when a producer goes offline.

Lab task 1:  python alert_subscriber.py --topic "factory/line3/+" --verbose
             (same threshold logic; non-numeric payloads such as 'online' are skipped)
"""
import argparse

from mqtt_common import HOST, PORT, make_client, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--topic", default="factory/+/temperature")
    ap.add_argument("--threshold", type=float, default=90.0)
    ap.add_argument("--verbose", action="store_true", help="print every received reading, not only alerts")
    a = ap.parse_args()

    c = make_client("")
    subs = [(a.topic, 1), ("factory/+/status", 1)]

    def on_connect(client, userdata, flags, rc, properties=None):
        log("ALERT-SUB", f"connected rc={rc}; subscribing to {[t for t, _ in subs]} at QoS 1 (threshold {a.threshold})")
        client.subscribe(subs)

    def on_message(client, userdata, msg):
        payload = msg.payload.decode()
        if msg.topic.endswith("/status"):
            log("ALERT-SUB", f"STATUS {msg.topic} = {payload}" + ("  (retained)" if msg.retain else ""))
            return
        try:
            value = float(payload)
        except ValueError:
            return
        if value > a.threshold:
            log("ALERT-SUB", f"ALERT {msg.topic} value {value} exceeds threshold {a.threshold}")
        elif a.verbose:
            log("ALERT-SUB", f"rx    {msg.topic} value {value}")

    c.on_connect, c.on_message = on_connect, on_message
    c.connect(a.host, a.port, keepalive=30)
    try:
        c.loop_forever()
    except KeyboardInterrupt:
        c.disconnect()


if __name__ == "__main__":
    main()
