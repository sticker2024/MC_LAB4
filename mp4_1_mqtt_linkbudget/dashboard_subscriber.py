#!/usr/bin/env python3
"""
Part A - step 6: operator dashboard.
Subscribes to factory/line3/temperature and factory/line3/status at QoS 1 and prints a
timestamped line per event. Messages delivered from the broker's retained store (because we
joined late) are labelled RETAINED.
"""
import argparse
import time

from mqtt_common import HOST, PORT, make_client, log

TOPICS = [("factory/line3/temperature", 1), ("factory/line3/status", 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--client-id", default="")
    ap.add_argument("--tag", default="DASH")
    a = ap.parse_args()

    c = make_client(a.client_id)

    def on_connect(client, userdata, flags, rc, properties=None):
        log(a.tag, f"connected rc={rc}; subscribing to {[t for t, _ in TOPICS]} at QoS 1")
        client.subscribe(TOPICS)

    def on_message(client, userdata, msg):
        flag = "  <-- RETAINED (delivered on subscribe)" if msg.retain else ""
        log(a.tag, f"{msg.topic:<28} {msg.payload.decode():<8} qos={msg.qos}{flag}")

    c.on_connect, c.on_message = on_connect, on_message
    c.connect(a.host, a.port, keepalive=30)
    try:
        c.loop_forever()
    except KeyboardInterrupt:
        c.disconnect()


if __name__ == "__main__":
    main()
