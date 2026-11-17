#!/usr/bin/env python3
"""Runs Lab tasks 1-3 for Mini Project 4.1 (task 3 starts its own broker, tasks 1-2 share one)."""
import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(HERE, "logs")
PY = sys.executable
env = dict(os.environ, PYTHONUNBUFFERED="1")


def logfile(n):
    return open(os.path.join(LOGS, n), "w")


def main():
    os.makedirs(LOGS, exist_ok=True); os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    broker = subprocess.Popen(["mosquitto", "-c", os.path.join(HERE, "mosquitto_test.conf")],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    print("== Lab task 1: humidity sensor + alert subscriber on factory/line3/+ ==")
    a = subprocess.Popen([PY, "alert_subscriber.py", "--topic", "factory/line3/+", "--verbose"],
                         cwd=HERE, stdout=logfile("labtask1_alert.log"), stderr=subprocess.STDOUT, env=env)
    time.sleep(1)
    p1 = subprocess.Popen([PY, "sensor_publisher.py", "--interval", "1", "--seed", "21"], cwd=HERE,
                          stdout=logfile("labtask1_temp_pub.log"), stderr=subprocess.STDOUT, env=env)
    p2 = subprocess.Popen([PY, "sensor_publisher.py", "--topic", "factory/line3/humidity",
                           "--client-id", "line3-hum-sensor", "--status-topic", "factory/line3/humstatus",
                           "--lo", "30", "--hi", "70", "--interval", "1", "--seed", "22"], cwd=HERE,
                          stdout=logfile("labtask1_hum_pub.log"), stderr=subprocess.STDOUT, env=env)
    time.sleep(9)
    for p in (p1, p2, a):
        p.send_signal(signal.SIGINT)
    for p in (p1, p2, a):
        p.wait()

    print("\n== Lab task 2: ungraceful disconnect at QoS 0 / 1 / 2 ==")
    with open(os.path.join(LOGS, "labtask2.log"), "w") as f:
        r = subprocess.run([PY, "labtask2_qos_crash.py"], cwd=HERE, stdout=subprocess.PIPE, text=True, env=env)
        f.write(r.stdout); print(r.stdout)
    broker.send_signal(signal.SIGTERM); broker.wait()

    print("== Lab task 3: broker outage, QoS 0 vs QoS 1 ==")
    with open(os.path.join(LOGS, "labtask3.log"), "w") as f:
        r = subprocess.run([PY, "labtask3_outage.py"], cwd=HERE, stdout=subprocess.PIPE, text=True, env=env)
        f.write(r.stdout); print(r.stdout)


if __name__ == "__main__":
    main()
