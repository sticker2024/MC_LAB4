#!/usr/bin/env python3
"""
Part A - step 3/4/5: simulated factory sensor.

  * client id "line3-temp-sensor"
  * Last Will and Testament registered BEFORE connect():
        topic factory/line3/status, payload "offline", QoS 1, retain=True
  * immediately after connecting publishes "online" (retain=True) to the same topic
  * every --interval seconds (default 5) publishes a random reading between 60 and 95
    to factory/line3/temperature at QoS 1
  * readings are published with retain=True so a late subscriber instantly sees the last
    known value (the very first reading is retained as the lab requires; we keep retaining
    each new one so the retained value is never stale - use --no-retain-all to retain only the first)

Examples
  python sensor_publisher.py
  python sensor_publisher.py --interval 1 --qos 0
  python sensor_publisher.py --topic factory/line3/humidity --client-id line3-hum-sensor \
         --status-topic factory/line3/humstatus --lo 30 --hi 70          # Lab task 1
"""
import argparse
import random
import time

from mqtt_common import HOST, PORT, make_client, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--client-id", default="line3-temp-sensor")
    ap.add_argument("--topic", default="factory/line3/temperature")
    ap.add_argument("--status-topic", default="factory/line3/status")
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--qos", type=int, default=1, choices=[0, 1, 2])
    ap.add_argument("--lo", type=float, default=60.0)
    ap.add_argument("--hi", type=float, default=95.0)
    ap.add_argument("--keepalive", type=int, default=5)
    ap.add_argument("--count", type=int, default=0, help="stop after N readings (0 = run forever)")
    ap.add_argument("--no-retain-all", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    if a.seed is not None:
        random.seed(a.seed)

    c = make_client(a.client_id)
    # --- Last Will and Testament: must be set before connect()
    c.will_set(a.status_topic, payload="offline", qos=1, retain=True)

    def on_connect(client, userdata, flags, rc, properties=None):
        log("PUB", f"connected to {a.host}:{a.port} rc={rc} - LWT registered on {a.status_topic}")
        # announce presence; retained so any new subscriber sees current status
        client.publish(a.status_topic, "online", qos=1, retain=True)
        log("PUB", f"{a.status_topic} <- 'online' (retain=True)")

    def on_publish(client, userdata, mid, *args):
        log("PUB", f"broker acknowledged mid={mid}")

    c.on_connect = on_connect
    c.on_publish = on_publish
    c.connect(a.host, a.port, keepalive=a.keepalive)
    c.loop_start()
    time.sleep(0.5)

    n = 0
    try:
        while True:
            value = round(random.uniform(a.lo, a.hi), 2)
            retain = (n == 0) or (not a.no_retain_all)
            info = c.publish(a.topic, f"{value}", qos=a.qos, retain=retain)
            log("PUB", f"{a.topic} <- {value}  (qos={a.qos}, retain={retain}, mid={info.mid})")
            n += 1
            if a.count and n >= a.count:
                break
            time.sleep(a.interval)
    except KeyboardInterrupt:
        pass
    # clean exit => broker does NOT publish the LWT
    c.disconnect()
    c.loop_stop()
    log("PUB", "clean disconnect (no LWT will be published)")


if __name__ == "__main__":
    main()
