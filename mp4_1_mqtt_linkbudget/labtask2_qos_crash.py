#!/usr/bin/env python3
"""
Lab task 2: repeat the ungraceful-disconnect demonstration at QoS 0, 1 and 2 and record whether
the final reading sent just before the crash is received.

For every (QoS, delay) pair we start crash_publisher.py N times. A listener (subscribed at QoS 2
so the grant is never downgraded) counts how many of the N final messages arrive.
Needs a broker on localhost:1883 (run_lab_tasks.py starts one).
"""
import csv
import os
import subprocess
import sys
import threading
import time

from mqtt_common import make_client

HERE = os.path.dirname(os.path.abspath(__file__))
TRIALS = int(os.environ.get("TRIALS", "30"))
DELAYS = ["0", "1", "5", "50", "ack"]
TOPIC = "factory/line3/crashtest"


def run():
    got, lock = set(), threading.Lock()
    l = make_client("crash-listener")

    def on_connect(c, u, f, rc, p=None):
        c.subscribe(TOPIC, qos=2)

    def on_message(c, u, m):
        with lock:
            got.add(m.payload.decode())

    l.on_connect, l.on_message = on_connect, on_message
    l.connect("localhost", 1883); l.loop_start(); time.sleep(0.5)

    results = {}
    for qos in (0, 1, 2):
        for d in DELAYS:
            ok = 0
            for t in range(TRIALS):
                tag = f"q{qos}d{d}t{t}"
                subprocess.run([sys.executable, os.path.join(HERE, "crash_publisher.py"), "--qos", str(qos),
                                "--delay-ms", d, "--payload", tag],
                               cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.15)
                with lock:
                    ok += tag in got
            results[(qos, d)] = ok
            print(f"QoS {qos}  crash {d:>3}{'' if d=='ack' else ' ms'} after publish() : {ok:2d}/{TRIALS} final readings received", flush=True)
    l.loop_stop(); l.disconnect()

    with open(os.path.join(HERE, "results", "labtask2_qos_crash.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["qos"] + [f"delay_{d}" for d in DELAYS] + ["trials"])
        for q in (0, 1, 2):
            w.writerow([q] + [results[(q, d)] for d in DELAYS] + [TRIALS])


if __name__ == "__main__":
    run()
