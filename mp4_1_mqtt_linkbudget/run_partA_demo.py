#!/usr/bin/env python3
"""
Automates the Part A procedure (steps 8-10) against a local Mosquitto broker and writes one
log file per 'terminal' into ./logs :

  1. start broker, dashboard, alert subscriber, then sensor_publisher         (step 8)
  2. stop dashboard and restart it while the publisher keeps running         (step 9, retained msgs)
  3. kill -9 the publisher (ungraceful) -> broker publishes the LWT          (step 10)

For speed the demo publishes every 1 s (the lab default is 5 s: just drop --interval).
Run:  python run_partA_demo.py
"""
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(HERE, "logs")
os.makedirs(LOGS, exist_ok=True)
PY = sys.executable
env = dict(os.environ, PYTHONUNBUFFERED="1")


def spawn(script_args, logname):
    f = open(os.path.join(LOGS, logname), "w")
    return subprocess.Popen([PY] + script_args, cwd=HERE, stdout=f, stderr=subprocess.STDOUT, env=env), f


def clear_retained(topics):
    """Publish an empty retained payload = delete the retained message (paho only, no mosquitto_pub needed)."""
    from mqtt_common import make_client
    c = make_client("cleaner")
    c.connect("localhost", 1883)
    c.loop_start()
    for t in topics:
        c.publish(t, b"", qos=1, retain=True).wait_for_publish()
    c.loop_stop(); c.disconnect()


def main():
    broker_log = open(os.path.join(LOGS, "broker.log"), "w")
    broker = subprocess.Popen(["mosquitto", "-c", os.path.join(HERE, "mosquitto_test.conf"), "-v"],
                              stdout=broker_log, stderr=subprocess.STDOUT)
    time.sleep(1.0)
    print("broker started")
    # clear any retained state from a previous run so the demo starts clean
    clear_retained(["factory/line3/status", "factory/line3/temperature"])

    dash, f1 = spawn(["dashboard_subscriber.py", "--tag", "DASH"], "dashboard.log")
    alert, f2 = spawn(["alert_subscriber.py"], "alert.log")
    time.sleep(1.0)
    pub, f3 = spawn(["sensor_publisher.py", "--interval", "1", "--seed", "4"], "publisher.log")
    print("running normal operation (14 s)...")
    time.sleep(14)

    print("stopping dashboard and restarting it (late joiner)...")
    dash.send_signal(signal.SIGTERM); dash.wait(); f1.close()
    time.sleep(2.5)       # the publisher keeps running meanwhile
    dash2, f4 = spawn(["dashboard_subscriber.py", "--tag", "DASH-restarted"], "dashboard_restarted.log")
    time.sleep(5)

    print("killing publisher with SIGKILL (ungraceful)...")
    with open(os.path.join(LOGS, "events.log"), "a") as ev:
        ev.write(f"{time.strftime('%H:%M:%S')} $ kill -9 {pub.pid}   # sensor_publisher.py\n")
    pub.send_signal(signal.SIGKILL); pub.wait()
    time.sleep(4)
    for p in (dash2, alert):
        p.send_signal(signal.SIGTERM)
        p.wait()
    broker.send_signal(signal.SIGTERM); broker.wait()
    for f in (f2, f3, f4, broker_log):
        f.close()
    print("done - see ./logs")


if __name__ == "__main__":
    main()
