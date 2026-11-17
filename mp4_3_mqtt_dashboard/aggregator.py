#!/usr/bin/env python3
"""
Aggregator / logger: ONE wildcard subscription (plant1/+/+, QoS 1).
  * timestamps and stores every reading in memory (dict keyed by topic) and in readings_log.csv
  * prints a summary of the latest value per topic every --summary seconds
  * recognises new topics automatically (no code change) and tracks <line>/status events
"""
import argparse
import csv
import os
import threading
import time

from mqtt_common import HOST, PORT, make_client, log, ts

ap = argparse.ArgumentParser()
ap.add_argument("--filter", default="plant1/+/+")
ap.add_argument("--summary", type=float, default=5.0)
ap.add_argument("--csv", default="readings_log.csv")
ap.add_argument("--tag", default="AGG")
a = ap.parse_args()

latest, count, status, lock = {}, {}, {}, threading.Lock()
newfile = not os.path.exists(a.csv)
fh = open(a.csv, "a", newline="")
wr = csv.writer(fh)
if newfile:
    wr.writerow(["timestamp", "topic", "value", "retained"])


def on_connect(cl, u, f, rc, p=None):
    log(a.tag, f"connected rc={rc}; single wildcard subscription '{a.filter}' at QoS 1")
    cl.subscribe(a.filter, qos=1)


def on_message(cl, u, m):
    payload = m.payload.decode()
    if not payload:
        return
    with lock:
        if m.topic.endswith("/status"):
            status[m.topic] = payload
            log(a.tag, f"STATUS {m.topic} = {payload}" + ("  <-- RETAINED" if m.retain else ""))
            return
        if m.topic not in latest:
            log(a.tag, f"NEW TOPIC discovered: {m.topic}  (no code change needed)")
        latest[m.topic] = (ts(), payload)
        count[m.topic] = count.get(m.topic, 0) + 1
        wr.writerow([ts(), m.topic, payload, int(m.retain)]); fh.flush()
        if m.retain:
            log(a.tag, f"{m.topic} = {payload}  <-- RETAINED last-known value delivered on subscribe")


def summary():
    while True:
        time.sleep(a.summary)
        with lock:
            lines = [f"  {t:<28} latest={v[1]:<8} at {v[0]}  n={count[t]}" for t, v in sorted(latest.items())]
            st = ", ".join(f"{k.split('/')[1]}={v}" for k, v in sorted(status.items()))
        log(a.tag, f"---- SUMMARY ({len(lines)} topics; status: {st or 'n/a'}) ----")
        for l in lines:
            print(l, flush=True)


c = make_client("")
c.on_connect, c.on_message = on_connect, on_message
c.connect(HOST, PORT, keepalive=30)
threading.Thread(target=summary, daemon=True).start()
try:
    c.loop_forever()
except KeyboardInterrupt:
    c.disconnect()
