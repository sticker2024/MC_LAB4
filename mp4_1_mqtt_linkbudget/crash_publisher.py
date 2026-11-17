#!/usr/bin/env python3
"""Lab task 2 helper: publish ONE message at the given QoS, then die with SIGKILL.

  python crash_publisher.py --qos 1 --delay-ms 0 --payload trial7
  --delay-ms N   : sleep N ms after publish() returns, then kill -9
  --delay-ms ack : wait_for_publish() (QoS 1/2 handshake complete) and only then kill -9
"""
import argparse
import os
import signal
import threading
import time

from mqtt_common import HOST, PORT, make_client

ap = argparse.ArgumentParser()
ap.add_argument("--qos", type=int, default=1)
ap.add_argument("--delay-ms", default="0")
ap.add_argument("--payload", default="x")
ap.add_argument("--topic", default="factory/line3/crashtest")
a = ap.parse_args()

connected = threading.Event()
c = make_client("crash-pub-" + a.payload)
c.on_connect = lambda *args, **kw: connected.set()
c.connect(HOST, PORT, keepalive=5)
c.loop_start()
connected.wait(2)
info = c.publish(a.topic, a.payload, qos=a.qos)       # returns as soon as the packet is queued
if a.delay_ms == "ack":
    info.wait_for_publish(2)
else:
    time.sleep(int(a.delay_ms) / 1000.0)
os.kill(os.getpid(), signal.SIGKILL)                   # ungraceful: no DISCONNECT, no flush
