#!/usr/bin/env python3
"""Lab task 3 helper: persistent-session subscriber that records every sequence number received."""
import argparse
import json
import signal
import sys
from mqtt_common import HOST, PORT, make_client

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--reconnect", type=float, default=1.0)
a = ap.parse_args()
seqs = []

try:
    c = make_client("task3-sub", clean_session=False)      # persistent session
except TypeError:
    c = make_client("task3-sub")
c.reconnect_delay_set(min_delay=a.reconnect, max_delay=a.reconnect)
import time as _t
EVENTS = []


def _on_connect(cl, u, f, rc, p=None):
    sp = getattr(f, "session_present", None) if not isinstance(f, dict) else f.get("session_present")
    EVENTS.append((round(_t.time() % 1000, 2), "SUB connected", f"session_present={sp}"))
    cl.subscribe("factory/line3/outage", qos=1)


c.on_connect = _on_connect
c.on_message = lambda cl, u, m: seqs.append(int(m.payload))


def stop(*_):
    json.dump(seqs, open(a.out, "w"))
    json.dump(EVENTS, open(a.out + ".events", "w"))
    sys.exit(0)


signal.signal(signal.SIGTERM, stop)
c.connect_async(HOST, PORT, keepalive=3)
c.loop_forever()
