#!/usr/bin/env python3
"""
Generic simulated plant sensor (one process per sensor, each with its own interval, QoS 1).

  python plant_sensor.py --topic plant1/lineA/temperature --kind temperature --interval 1 --lwt
  python plant_sensor.py --topic plant1/lineA/vibration  --kind vibration   --interval 0.5
  python plant_sensor.py --topic plant1/lineB/temperature --kind temperature --interval 1.5 --lwt

--lwt   registers a Last Will on plant1/<line>/status ("offline", retained) and announces "online" (retained)
Every reading is published retained, so a late subscriber immediately sees the last value of every topic.
"""
import argparse
import random
import time

from mqtt_common import HOST, PORT, make_client, log

ap = argparse.ArgumentParser()
ap.add_argument("--topic", required=True)
ap.add_argument("--kind", choices=["temperature", "vibration", "humidity"], required=True)
ap.add_argument("--interval", type=float, default=2.0)
ap.add_argument("--qos", type=int, default=1)
ap.add_argument("--lwt", action="store_true")
ap.add_argument("--count", type=int, default=0)
ap.add_argument("--seed", type=int, default=None)
a = ap.parse_args()
if a.seed is not None:
    random.seed(a.seed)

line_prefix = a.topic.rsplit("/", 1)[0]
status_topic = line_prefix + "/status"
cid = "sensor-" + a.topic.replace("/", "-")
c = make_client(cid)
if a.lwt:
    c.will_set(status_topic, "offline", qos=1, retain=True)       # before connect()


def on_connect(cl, u, f, rc, p=None):
    log("SENSOR", f"{a.topic} connected rc={rc}" + (f", LWT on {status_topic}" if a.lwt else ""))
    if a.lwt:
        cl.publish(status_topic, "online", qos=1, retain=True)


c.on_connect = on_connect
c.connect(HOST, PORT, keepalive=5)
c.loop_start()
time.sleep(0.5)

PARAMS = {"temperature": (72.0, 3.0, 0.12, 18.0), "vibration": (2.0, 0.4, 0.10, 3.5), "humidity": (50.0, 4.0, 0.05, 20.0)}
mean, sd, p_spike, spike = PARAMS[a.kind]
n = 0
try:
    while True:
        v = random.gauss(mean, sd) + (random.uniform(0.6, 1.0) * spike if random.random() < p_spike else 0.0)
        v = round(max(v, 0.0), 2)
        c.publish(a.topic, str(v), qos=a.qos, retain=True)
        log("SENSOR", f"{a.topic} <- {v}")
        n += 1
        if a.count and n >= a.count:
            break
        time.sleep(a.interval)
except KeyboardInterrupt:
    pass
c.disconnect(); c.loop_stop()
