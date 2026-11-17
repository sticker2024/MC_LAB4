"""Builds terminal-style screenshots of the real console logs -> ../screenshots/"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from term_shot import render
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(R, "screenshots"); os.makedirs(OUT, exist_ok=True)
P1, P2, P3 = (os.path.join(R, d) for d in ("mp4_1_mqtt_linkbudget", "mp4_2_iot_selector", "mp4_3_mqtt_dashboard"))

def lines(path):
    return open(path).read().rstrip("\n").split("\n")

def shot(name, title, body, size=13, width=None):
    render("\n".join(body), os.path.join(OUT, name), title, size=size, width_chars=width)

L = lambda f: lines(os.path.join(P1, "logs", f))
shot("4_1_A1_publisher_normal.png", "Terminal 4: python sensor_publisher.py --interval 1", ["$ python sensor_publisher.py --interval 1"] + L("publisher.log")[:14], 13, 120)
shot("4_1_A2_dashboard_normal.png", "Terminal 2: python dashboard_subscriber.py", ["$ python dashboard_subscriber.py"] + L("dashboard.log")[:14], 13, 120)
shot("4_1_A3_alert_normal.png", "Terminal 3: python alert_subscriber.py  (threshold 90.0)", ["$ python alert_subscriber.py"] + L("alert.log")[:6], 13, 140)
shot("4_1_A4_dashboard_restarted_retained.png", "Dashboard restarted mid-run: retained messages delivered at once",
     ["$ python dashboard_subscriber.py --tag DASH-restarted   # publisher still running"] + L("dashboard_restarted.log")[:8], 13, 120)
alert = L("alert.log"); dr = L("dashboard_restarted.log"); brk = L("broker.log")
i = max(k for k, x in enumerate(brk) if "closed its connection" in x and "line3-temp-sensor" in x)
shot("4_1_A5_lwt_ungraceful.png", "kill -9 sensor_publisher.py  ->  broker publishes the Last Will",
     L("events.log") + ["", "--- broker log (mosquitto -v) ---"] + [x[x.index(":")+2:] if ": " in x else x for x in brk[i-1:i+5]] +
     ["", "--- dashboard (restarted) ---"] + dr[-2:] + ["", "--- alert subscriber ---"] + alert[-1:], 13, 150)
shot("4_1_labtask1_wildcard.png", "Lab task 1: alert subscriber on factory/line3/+ (temperature AND humidity)",
     ["$ python alert_subscriber.py --topic 'factory/line3/+' --verbose"] + L("labtask1_alert.log")[:12], 13, 120)
shot("4_1_labtask2_qos_crash.png", "Lab task 2: final reading received after kill -9 (30 trials per cell)", ["$ python labtask2_qos_crash.py"] + L("labtask2.log"), 13)
shot("4_1_labtask3_outage.png", "Lab task 3: broker outage, subscriber re-subscribes first (3 runs each)",
     ["$ MODE=ordered python labtask3_outage.py"] + [x for x in L("labtask3_ordered.log") if "events:" not in x], 12, 130)
pb = lines(os.path.join(P1, "results", "partB_console.txt"))
shot("4_1_B1_table.png", "$ python link_budget_compare.py   (Part B comparison)", ["$ python link_budget_compare.py"] + pb[:21], 12, 160)
shot("4_1_B2_labtask4_container.png", "Lab task 4: container / ocean crossing", pb[22:49], 12, 130)
shot("4_1_B3_labtask5_6.png", "Lab tasks 5 and 6: RedCap and path-loss exponent", pb[49:], 12, 130)
s = lines(os.path.join(P2, "results", "console_log.txt"))
shot("4_2_selector_S1_S2.png", "$ python iot_selector.py   (scenarios S1, S2)", ["$ python iot_selector.py"] + s[:33], 12, 150)
shot("4_2_selector_summary.png", "$ python iot_selector.py   (summary of all five scenarios)", s[-7:], 13)
T = lambda f: lines(os.path.join(P3, "logs", f))
shot("4_3_A_aggregator_summary.png", "Aggregator: one wildcard subscription plant1/+/+ , periodic summary", ["$ python aggregator.py"] + T("aggregator.log")[:14], 13, 130)
shot("4_3_B_alerts.png", "Alert subscriber: independent per-topic thresholds", ["$ python alert_subscriber.py"] + T("alert.log")[:10], 13, 130)
shot("4_3_C_retained_late_joiner.png", "Late-joining aggregator receives retained values immediately", ["$ python aggregator.py --csv readings_log_late.csv --tag AGG-late"] + T("aggregator_late.log")[:12], 13, 130)
agg = T("aggregator.log")
new = [x for x in agg if "NEW TOPIC" in x and "lineB/vibration" in x]
late = T("aggregator_late.log"); newl = [x for x in late if "lineB/vibration" in x][:2]
shot("4_3_D_new_topic_no_code_change.png", "New sensor plant1/lineB/vibration started while running",
     ["$ python plant_sensor.py --topic plant1/lineB/vibration --kind vibration --interval 0.7"] + T("sensor_lineB_vibration_NEW.log")[:2] +
     ["", "--- aggregator.py (unchanged code) ---"] + new + ["", "--- late aggregator ---"] + newl[:1], 13, 130)
st = [x for x in agg if "offline" in x]
shot("4_3_E_lwt.png", "kill -9 lineB temperature sensor -> LWT", T("events.log") + ["", "--- aggregator ---"] + st + ["", "--- alert subscriber ---"] + [x for x in T("alert.log") if "OFFLINE" in x], 13, 140)
print("MC screenshots done")
