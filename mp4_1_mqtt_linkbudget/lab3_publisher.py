#!/usr/bin/env python3
"""Lab task 3 helper: publish sequence numbers 1..N every 0.2 s at the chosen QoS, with auto-reconnect."""
import argparse
import time
from mqtt_common import HOST, PORT, make_client

ap = argparse.ArgumentParser()
ap.add_argument("--qos", type=int, required=True)
ap.add_argument("--n", type=int, default=150)
ap.add_argument("--interval", type=float, default=0.2)
ap.add_argument("--reconnect", type=float, default=2.0, help="fixed reconnect delay (s)")
a = ap.parse_args()

c = make_client(f"task3-pub-q{a.qos}")
c.reconnect_delay_set(min_delay=a.reconnect, max_delay=a.reconnect)
import json as _j
EV = []
c.on_connect = lambda cl, u, f, rc, pr=None: EV.append((round(time.time() % 1000, 2), "PUB connected"))
c.on_disconnect = lambda cl, u, *a_: EV.append((round(time.time() % 1000, 2), "PUB disconnected"))
c.connect_async(HOST, PORT, keepalive=3)
c.loop_start()
time.sleep(0.5)
for seq in range(1, a.n + 1):
    info = c.publish("factory/line3/outage", str(seq), qos=a.qos)
    time.sleep(a.interval)
time.sleep(6)            # give QoS 1 time to flush its backlog after reconnect
c.disconnect(); c.loop_stop()
_j.dump(EV, open(f"/tmp/pub_events_q{a.qos}.json", "w"))
print("publisher finished", a.n, "messages published (publish() calls)")
