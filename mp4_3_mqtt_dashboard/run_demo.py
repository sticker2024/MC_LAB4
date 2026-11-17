#!/usr/bin/env python3
"""
Runs the whole Mini Project 4.3 demonstration against a local Mosquitto broker and writes logs/*.log

  t=0   broker, aggregator, alert subscriber, 3 sensors (A-temp+LWT, A-vib, B-temp+LWT)
  t=14  start a LATE aggregator           -> immediately receives retained values (retained demo)
  t=20  start a NEW sensor plant1/lineB/vibration -> both subscribers pick it up with no code change
  t=30  kill -9 the lineB temperature sensor      -> broker publishes LWT 'offline' (LWT demo)
  t=36  shut everything down
(intervals are shortened to 0.5-1.5 s so the demo is quick)
"""
import os, signal, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LOGS = os.path.join(HERE, "logs"); os.makedirs(LOGS, exist_ok=True)
PY = sys.executable
env = dict(os.environ, PYTHONUNBUFFERED="1")


def spawn(args, log):
    f = open(os.path.join(LOGS, log), "w")
    return subprocess.Popen([PY] + args, cwd=HERE, stdout=f, stderr=subprocess.STDOUT, env=env)


def clear(topics):
    from mqtt_common import make_client
    c = make_client("cleaner"); c.connect("localhost", 1883); c.loop_start()
    for t in topics:
        c.publish(t, b"", qos=1, retain=True).wait_for_publish()
    c.loop_stop(); c.disconnect()


def main():
    for f in ("readings_log.csv", "readings_log_late.csv"):
        if os.path.exists(os.path.join(HERE, f)):
            os.remove(os.path.join(HERE, f))
    broker = subprocess.Popen(["mosquitto", "-c", os.path.join(HERE, "mosquitto_test.conf"), "-v"],
                              stdout=open(os.path.join(LOGS, "broker.log"), "w"), stderr=subprocess.STDOUT)
    time.sleep(1)
    clear([f"plant1/{l}/{k}" for l in ("lineA", "lineB") for k in ("temperature", "vibration", "status")])
    agg = spawn(["aggregator.py", "--summary", "6"], "aggregator.log")
    alert = spawn(["alert_subscriber.py"], "alert.log")
    time.sleep(1)
    sA = spawn(["plant_sensor.py", "--topic", "plant1/lineA/temperature", "--kind", "temperature", "--interval", "1", "--lwt", "--seed", "1"], "sensor_lineA_temperature.log")
    sV = spawn(["plant_sensor.py", "--topic", "plant1/lineA/vibration", "--kind", "vibration", "--interval", "0.5", "--seed", "2"], "sensor_lineA_vibration.log")
    sB = spawn(["plant_sensor.py", "--topic", "plant1/lineB/temperature", "--kind", "temperature", "--interval", "1.5", "--lwt", "--seed", "3"], "sensor_lineB_temperature.log")
    time.sleep(14)
    print("late-joining aggregator ...")
    late = spawn(["aggregator.py", "--summary", "6", "--csv", "readings_log_late.csv", "--tag", "AGG-late"], "aggregator_late.log")
    time.sleep(6)
    print("adding NEW sensor plant1/lineB/vibration while the system runs ...")
    sN = spawn(["plant_sensor.py", "--topic", "plant1/lineB/vibration", "--kind", "vibration", "--interval", "0.7", "--seed", "5"], "sensor_lineB_vibration_NEW.log")
    time.sleep(10)
    print("kill -9 lineB temperature sensor ...")
    with open(os.path.join(LOGS, "events.log"), "w") as ev:
        ev.write(f"$ kill -9 {sB.pid}     # plant_sensor.py --topic plant1/lineB/temperature  (has LWT)\n")
    sB.send_signal(signal.SIGKILL); sB.wait()
    time.sleep(6)
    for p in (sA, sV, sN, agg, late, alert):
        p.send_signal(signal.SIGTERM)
    for p in (sA, sV, sN, agg, late, alert):
        p.wait()
    broker.send_signal(signal.SIGTERM); broker.wait()
    print("done")


if __name__ == "__main__":
    main()
