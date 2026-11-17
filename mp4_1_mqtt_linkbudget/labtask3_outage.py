#!/usr/bin/env python3
"""
Lab task 3: intentionally unreliable network. While a publisher sends 100 numbered readings
(one every 0.2 s) the broker is stopped for 3 s and restarted, once with the publisher at QoS 0
and once at QoS 1. We count how many readings never reach the subscriber.
The broker uses persistence so the subscriber's persistent QoS 1 session survives the restart.
"""
import csv
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
N = 100
MODE = os.environ.get("MODE", "ordered")   # ordered: subscriber retries every 0.25 s, publisher every 2 s; race: both 1.5 s


def start_broker(conf):
    return subprocess.Popen(["mosquitto", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def one_run(qos):
    tmp = tempfile.mkdtemp()
    conf = os.path.join(tmp, "m.conf")
    open(conf, "w").write(f"listener 1883 127.0.0.1\nallow_anonymous true\npersistence true\n"
                          f"persistence_location {tmp}/\nautosave_interval 1\n")
    broker = start_broker(conf)
    time.sleep(1)
    out = os.path.join(tmp, "got.json")
    sub_rc, pub_rc = (("0.25", "2") if MODE == "ordered" else ("1.5", "1.5"))
    sub = subprocess.Popen([PY, "lab3_subscriber.py", "--out", out, "--reconnect", sub_rc], cwd=HERE)
    time.sleep(1)
    pub = subprocess.Popen([PY, "lab3_publisher.py", "--qos", str(qos), "--n", str(N), "--reconnect", pub_rc], cwd=HERE,
                           stdout=subprocess.PIPE, text=True)
    time.sleep(6)
    broker.send_signal(signal.SIGTERM); broker.wait()                 # network outage begins
    print(f"  [QoS {qos}] broker DOWN", flush=True)
    time.sleep(3)
    broker = start_broker(conf)                                      # outage ends
    print(f"  [QoS {qos}] broker back up", flush=True)
    pub.wait(timeout=60)
    time.sleep(4)
    sub.send_signal(signal.SIGTERM); sub.wait()
    broker.send_signal(signal.SIGTERM); broker.wait()
    got = json.load(open(out))
    try:
        sev = json.load(open(out + ".events")); pev = json.load(open(f"/tmp/pub_events_q{qos}.json"))
        evs = sorted([tuple(e) for e in sev] + [tuple(e) for e in pev])
        print("   events: " + " | ".join(f"{e[0]:.1f}s {e[1]} {e[2] if len(e) > 2 else ''}".strip() for e in evs), flush=True)
    except Exception as ex:
        print("   (no event log)", ex)
    uniq = sorted(set(got))
    lost = [s for s in range(1, N + 1) if s not in uniq]
    return {"qos": qos, "published": N, "received_unique": len(uniq), "lost": len(lost),
            "duplicates": len(got) - len(uniq),
            "first_lost": lost[0] if lost else None, "last_lost": lost[-1] if lost else None}


if __name__ == "__main__":
    REPS = int(os.environ.get("REPS", "3"))
    rows = []
    for rep in range(1, REPS + 1):
        for q in [int(x) for x in os.environ.get('QOS', '0,1').split(',')]:
            print(f"run {rep}/{REPS} with publisher QoS {q}", flush=True)
            r = one_run(q)
            r["run"] = rep
            rows.append(r)
            print(f"  published {r['published']}  received {r['received_unique']}  LOST {r['lost']}  "
                  f"duplicates {r['duplicates']}  (lost seq {r['first_lost']}..{r['last_lost']})", flush=True)
    for q in (0, 1):
        lost = [r["lost"] for r in rows if r["qos"] == q]
        if lost:
            print(f"SUMMARY QoS {q} ({MODE} mode): lost per run = {lost}  mean = {sum(lost)/len(lost):.1f} of {N}")
    with open(os.path.join(HERE, "results", f"labtask3_outage_{MODE}.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
