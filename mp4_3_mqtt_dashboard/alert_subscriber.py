#!/usr/bin/env python3
"""
Independent per-topic threshold alerting (separate subscriber, single wildcard plant1/+/+).
Thresholds are looked up per topic (TOPIC_OVERRIDES) and otherwise per measurement type
(temperature vs vibration have different limits). A new topic is covered automatically.
"""
import argparse

from mqtt_common import HOST, PORT, make_client, log

THRESHOLDS = {"temperature": 85.0, "vibration": 4.5, "humidity": 65.0}      # per measurement type
TOPIC_OVERRIDES = {"plant1/lineB/temperature": 80.0}                         # per topic (line B runs cooler)

ap = argparse.ArgumentParser()
ap.add_argument("--filter", default="plant1/+/+")
a = ap.parse_args()


def limit_for(topic):
    return TOPIC_OVERRIDES.get(topic, THRESHOLDS.get(topic.rsplit("/", 1)[1]))


def on_connect(cl, u, f, rc, p=None):
    log("ALERT", f"connected rc={rc}; subscribing '{a.filter}'; thresholds {THRESHOLDS} overrides {TOPIC_OVERRIDES}")
    cl.subscribe(a.filter, qos=1)


def on_message(cl, u, m):
    if m.topic.endswith("/status"):
        if m.payload.decode() == "offline":
            log("ALERT", f"OFFLINE {m.topic} - publisher lost (Last Will delivered by broker)")
        return
    lim = limit_for(m.topic)
    try:
        v = float(m.payload)
    except ValueError:
        return
    if lim is not None and v > lim:
        log("ALERT", f"ALERT {m.topic} = {v} exceeds {lim}")


c = make_client("")
c.on_connect, c.on_message = on_connect, on_message
c.connect(HOST, PORT, keepalive=30)
try:
    c.loop_forever()
except KeyboardInterrupt:
    c.disconnect()
