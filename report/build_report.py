#!/usr/bin/env python3
"""Builds MC_Unit4_Lab_Report.docx from the logs/results of the three mini projects."""
import csv, os, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "tools")); sys.path.insert(0, os.path.join(R, "mp4_2_iot_selector"))
from report_lib import *
import iot_selector as S

def rd(p): return list(csv.DictReader(open(os.path.join(R, p))))
def f(x, n=1): return f"{float(x):.{n}f}"
SH = os.path.join(R, "screenshots"); A, B, C = "mp4_1_mqtt_linkbudget", "mp4_2_iot_selector", "mp4_3_mqtt_dashboard"
def shot(n, cap, w=6.4): figure(d, os.path.join(SH, n), cap, w)

d = new_doc()
title_page(d, "Mobile Communications", "Unit 4 - Mini Projects: Lab Report",
           "4.1 MQTT publish/subscribe + LPWAN link budget | 4.2 IoT connectivity selector | 4.3 Multi-sensor MQTT dashboard")

h(d, "1. Overview and how to reproduce")
para(d, "Three mini projects: an MQTT publish/subscribe system (topics, QoS, retained messages, Last Will) with an LPWAN link-budget comparison; a rule-based IoT technology selector; and a multi-sensor MQTT monitoring dashboard. "
        "All MQTT results were obtained against a real local Mosquitto 2.0.18 broker (localhost:1883) with paho-mqtt 2.2 and Python 3.12; nothing is mocked.")
table(d, ["Project", "Main files", "Run"],
      [["4.1 Part A", "mqtt_common.py, sensor_publisher.py, dashboard_subscriber.py, alert_subscriber.py, run_partA_demo.py", "python run_partA_demo.py (starts broker + all clients)"],
       ["4.1 Lab tasks 1-3", "crash_publisher.py, labtask2_qos_crash.py, labtask3_outage.py, lab3_*.py, run_lab_tasks.py", "python run_lab_tasks.py"],
       ["4.1 Part B + tasks 4-6", "link_budget_compare.py", "python link_budget_compare.py --all"],
       ["4.2", "iot_selector.py", "python iot_selector.py  (or --interactive)"],
       ["4.3", "plant_sensor.py, aggregator.py, alert_subscriber.py, run_demo.py", "python run_demo.py"]],
      widths=[1.3, 3.6, 1.9], size=8.5, caption="Table 1 - Files and commands")
para(d, "Console 'screenshots' are images rendered from the real captured logs of each run (tools/make_screenshots.py); replace them with genuine OS screenshots if your instructor requires that. "
        "For speed the automated demos publish every 0.5-1.5 s; the scripts default to the lab's 5 s (use --interval).", italic=True, size=10)

# ======================================================== 4.1
h(d, "2. Mini Project 4.1 - MQTT simulation and LPWAN link-budget comparison")
h(d, "2.1 Part A - design", 2)
bullets(d, [("sensor_publisher.py: ", "client id line3-temp-sensor; Last Will (factory/line3/status, 'offline', QoS 1, retain) is registered before connect(); 'online' (retained) is published in on_connect; a random 60-95 reading goes to factory/line3/temperature at QoS 1 with retain=True."),
            ("Deviation (documented): ", "the manual retains the first reading. We retain every reading so that the retained value is never stale; --no-retain-all gives the literal behaviour."),
            ("dashboard_subscriber.py: ", "subscribes to the temperature and status topics at QoS 1, prints a timestamped line per event and flags retained deliveries."),
            ("alert_subscriber.py: ", "wildcard factory/+/temperature at QoS 1; prints ALERT only above 90.0. It also subscribes to factory/+/status so that the 'LWT reaches both subscribers' observation holds (the literal subscription would never see the status topic)."),
            ("Keep-alive: ", "5 s. Because the publisher process is killed locally, the OS closes the TCP socket and Mosquitto publishes the will immediately; a silent network failure would take 1.5 x keep-alive.")])
h(d, "2.2 Part A - results", 2)
shot("4_1_A1_publisher_normal.png", "Screenshot 1 - Terminal 4: sensor_publisher.py (LWT registered, 'online' retained, QoS 1 publishes acknowledged)")
shot("4_1_A2_dashboard_normal.png", "Screenshot 2 - Terminal 2: dashboard_subscriber.py receives every reading")
shot("4_1_A3_alert_normal.png", "Screenshot 3 - Terminal 3: alert_subscriber.py reacts only to values above 90.0 (92.13 and 92.46)")
para(d, "Both subscribers received every reading from one publish call each (fan-out); only the alert subscriber reacted, and only to 92.13 and 92.46.")
shot("4_1_A4_dashboard_restarted_retained.png", "Screenshot 4 - dashboard restarted while the publisher keeps running: the retained temperature and status arrive within about 40 ms of connecting")
shot("4_1_A5_lwt_ungraceful.png", "Screenshot 5 - kill -9 of the publisher: the broker detects the closed connection and publishes the retained 'offline' will to both subscribers; the publisher executed no code")
para(d, "The clean shutdown path (client.disconnect(), used by Ctrl+C in sensor_publisher.py) logs 'clean disconnect' and does NOT trigger the will.")
h(d, "2.3 Lab tasks 1-3", 2)
shot("4_1_labtask1_wildcard.png", "Screenshot 6 - Lab task 1: second sensor on factory/line3/humidity; the alert subscriber now uses factory/line3/+ with unchanged threshold logic (non-numeric payloads are skipped)")
para(d, "Task 1: a humidity publisher (same script, --topic factory/line3/humidity) was added and the alert subscriber's filter changed to factory/line3/+; both measurements arrive without touching the threshold code (humidity 30-70 never exceeds 90, so it never alerts).")
c2 = rd(A + "/results/labtask2_qos_crash.csv")
table(d, ["QoS", "crash 0 ms", "1 ms", "5 ms", "50 ms", "after PUBACK/PUBCOMP"],
      [[r["qos"], f"{r['delay_0']}/{r['trials']}", f"{r['delay_1']}/{r['trials']}", f"{r['delay_5']}/{r['trials']}", f"{r['delay_50']}/{r['trials']}", f"{r['delay_ack']}/{r['trials']}"] for r in c2],
      widths=[0.6, 1.1, 1.0, 1.0, 1.0, 1.7], size=9, caption="Table 2 - Lab task 2: final reading received after kill -9 (30 trials per cell)")
shot("4_1_labtask2_qos_crash.png", "Screenshot 7 - Lab task 2 console output", 5.6)
para(d, "Task 2 finding: once a packet has left the host, the message is delivered at every QoS level, even though the publisher dies immediately; killing the process within microseconds of publish() loses the reading in a few trials at QoS 0 and QoS 1 (it never left the machine, which no QoS can repair) and in about half of the QoS 2 trials. "
        "QoS 2 is worse here because Mosquitto only forwards an inbound QoS 2 message to subscribers after the PUBREL step of the four-packet handshake, which a dead publisher never sends. QoS levels govern recovery between two live peers; they do not protect against a sender that dies before transmitting.")
c3 = rd(A + "/results/labtask3_outage_ordered.csv")
table(d, ["Run", "QoS", "published", "received", "lost", "duplicates"],
      [[r["run"], r["qos"], r["published"], r["received_unique"], r["lost"], r["duplicates"]] for r in sorted(c3, key=lambda r: (r["qos"], r["run"]))],
      widths=[0.7, 0.7, 1.0, 1.0, 0.8, 1.0], size=9, caption="Table 3 - Lab task 3: 3 s broker outage, 100 readings (controlled: subscriber re-subscribes first)")
shot("4_1_labtask3_outage.png", "Screenshot 8 - Lab task 3 console output", 5.8)
para(d, "Task 3 finding: the publisher at QoS 0 lost 19-20 readings every run (everything published while disconnected, about 4 s including reconnect back-off); at QoS 1 paho queued the messages and resent them after reconnecting, so nothing was lost. "
        "An earlier uncontrolled experiment showed an important caveat (results/labtask3_race_mode_observations.txt): when publisher and subscriber reconnect at the same moment, the QoS 1 backlog could reach the broker before the subscriber had re-subscribed (its log showed session_present=False), and then the whole backlog was dropped at the broker-to-subscriber hop in 3 of 9 uncontrolled QoS 1 runs (one further run lost a single message). "
        "QoS 1 protects each hop independently; end-to-end delivery also needs a subscriber that is subscribed (persistent session or prompt re-subscribe).")

h(d, "2.4 Part B - LPWAN link budget and battery life", 2)
para(d, "Scenario: 200 soil sensors on a 25 km2 farm, 12-byte reading every 30 minutes, maximum distance 8 km, 5-year target on 19 000 mAh, no cellular coverage nearby, no per-device fees preferred. Model: MCL = Ptx - Srx; PL(d) = 91.5 + 10 n log10(d / 1 km) with n = 3.5 gives PL(8 km) = 123.1 dB; margin = MCL - PL. "
        "Energy per 30-minute cycle = I_tx t_tx + I_rx t_rx + I_sleep (T - t_tx - t_rx). The currents and times are representative assumptions (listed below), not datasheet measurements; LoRaWAN time-on-air (1.48 s for a 25-byte frame at SF12) is computed from the Semtech formula.")
table(d, ["Technology", "Ptx", "Srx", "I_tx x t_tx", "RX windows", "Sleep"],
      [["NB-IoT", "23 dBm", "-129 dBm", "220 mA x 3.0 s", "-", "3 uA"], ["LTE-M (CE Mode B)", "23 dBm", "-125 dBm", "300 mA x 3.0 s", "-", "5 uA"],
       ["LoRaWAN SF12", "14 dBm", "-137 dBm", "44 mA x 1.48 s", "11 mA x 0.4 s", "2 uA"], ["5G RedCap (task 5)", "23 dBm", "-94 dBm", "400 mA x 1.5 s", "-", "50 uA"]],
      widths=[1.6, 0.8, 0.9, 1.4, 1.2, 0.8], size=8.5, caption="Table 4 - Assumed radio and energy parameters")
pb = rd(A + "/results/partB_comparison.csv")
table(d, ["Technology", "MCL (dB)", "PL 8 km (dB)", "Margin (dB)", "mAh / cycle", "mAh / year", "Life (y)", "Life incl. 1 %/y self-discharge (y)"],
      [[r["tech"], f(r["mcl_db"], 0), f(r["pl_db"]), f(r["margin_db"]), f(r["mah_cycle"], 4), f(r["mah_year"], 0), f(r["years"]), f(r["years_incl_selfdischarge"])] for r in pb],
      widths=[1.0, 0.7, 0.9, 0.8, 0.9, 0.8, 0.7, 1.3], size=8.5, caption="Table 5 - Part B comparison table")
figure(d, os.path.join(R, A, "figures", "partB_margin_and_life.png"), "Figure 1 - coverage margin at 8 km and estimated battery life", 6.0)
shot("4_1_B1_table.png", "Screenshot 9 - output of link_budget_compare.py", 6.5)
h(d, "Recommendation", 3)
just = ("LoRaWAN at SF12 with one or two privately owned gateways is recommended. All three technologies close the 8 km link with a positive margin, NB-IoT (28.9 dB) and LoRaWAN (27.9 dB) the deepest and LTE-M the smallest (24.9 dB), so coverage margin alone does not separate them and, as expected, battery life diverges more sharply: "
        "LTE-M's 300 mA bursts give about 4.1 years including self-discharge, below the 5-year target; NB-IoT just clears it at about 5.5 years; LoRaWAN uses about 356 mAh per year and would exceed 30 years, in practice limited by the cell's shelf life. "
        "The Section 4.3 axes then decide. The farm has no cellular coverage nearby, so NB-IoT and LTE-M margins are theoretical without an operator network, and both would add per-device subscriptions for 200 units, which the brief wants to avoid; LoRaWAN is infrastructure the farm owns once, with no per-device fee. "
        "Mobility is not needed and the data rate (12 bytes per 30 minutes) is far below LoRaWAN's limit; the duty cycle is 0.08 % against the 1 % limit and the total channel load is only about 0.16 s of airtime per second spread over several channels. "
        "The recommendation is insensitive to the path-loss exponent (task 6): the 10 dB reserve is only lost at n of about 5.5 for LoRaWAN. The main risk is the single gateway as a point of failure, which a second gateway would remove.")
para(d, just)
h(d, "2.5 Lab tasks 4-6", 2)
shot("4_1_B2_labtask4_container.png", "Screenshot 10 - Lab task 4: container ocean crossing", 6.2)
para(d, "Task 4: with the same MCLs the margin goes from about +60 dB at 1 km to 0 dB at only 41-54 km and is -45 dB at 1000 km (even free-space propagation leaves NB-IoT at about 0 dB at 1000 km). A single-distance calculation cannot justify a choice for the container because the distance to the nearest base station changes continuously along the route, because beyond the coast there is no terrestrial base station at all, "
        "and because the decision then rests on availability, roaming and satellite access (Section 4.3 axes) rather than on a point margin; each route segment needs its own budget, with satellite geometry for the ocean leg.")
rc = rd(A + "/results/labtask5_with_redcap.csv")
table(d, ["Technology", "MCL (dB)", "Margin at 8 km (dB)", "Life incl. self-discharge (y)"],
      [[r["tech"], f(r["mcl_db"], 0), f(r["margin_db"]), f(r["years_incl_selfdischarge"])] for r in rc], widths=[1.6, 1.0, 1.6, 2.0], size=9,
      caption="Table 6 - Lab task 5: RedCap added (representative values: -94 dBm sensitivity, 20 MHz)")
para(d, "Task 5: RedCap's wideband receiver gives an MCL of only about 117 dB, so it fails the 8 km link (-6.1 dB) even though its battery estimate is acceptable; it is a mid-rate cellular option, not an LPWAN.")
shot("4_1_B3_labtask5_6.png", "Screenshot 11 - Lab tasks 5 and 6", 6.2)
figure(d, os.path.join(R, A, "figures", "labtask6_margin_vs_n.png"), "Figure 2 - Lab task 6: margin at 8 km versus path-loss exponent", 4.8)
para(d, "Task 6: varying n from 2.5 to 4.0 moves the NB-IoT/LoRaWAN margins only from about 37 to 23-24 dB; the 10 dB reserve survives until n is about 5.5, so the recommended technology does not change. The choice is controlled by infrastructure and cost, not by this assumption; only RedCap's feasibility depends on n.")

# ======================================================== 4.2
d.add_page_break()
h(d, "3. Mini Project 4.2 - Rule-based IoT connectivity selector")
h(d, "3.1 Scoring methodology (one-page write-up)", 2)
para(d, "The selector scores five candidates - NB-IoT, LTE-M, LoRaWAN, 5G RedCap and short-range (BLE/Zigbee) - on the six Section 4.3 axes. Steps: (1) a 0-5 capability matrix; (2) the requirement is mapped onto the same scale; (3) per-axis suitability; (4) weighted sum scaled to 0-100; (5) rule-based constraints; (6) ranked output with a justification naming strong and weak axes and the rules fired. "
        "NOTE: the manual's Section 4.2/4.3 tables were not available while building this, so the matrix encodes the standard comparison (NB-IoT deep coverage and battery; LTE-M mobility and mid rate; LoRaWAN private long range at low cost; RedCap high rate and cost; BLE/Zigbee short range, cheapest). Edit the CAPABILITY dict to match your tables; no other code changes.")
ord_axes = [("data_rate", "Data rate"), ("battery", "Battery"), ("cost", "Cost at scale")]
table(d, ["Axis (0-5)"] + S.TECHS, [[n] + [S.CAPABILITY[a][t] for t in S.TECHS] for a, n in ord_axes],
      widths=[1.4, 1.0, 1.0, 1.0, 1.1, 1.2], size=9, caption="Table 7 - Capability matrix, ordinal axes")
rows = []
for a, n in (("coverage", "Coverage"), ("mobility", "Mobility"), ("infrastructure", "Infrastructure")):
    for cat, vals in S.CAPABILITY[a].items():
        rows.append([f"{n}: {cat}"] + [vals[t] for t in S.TECHS])
table(d, ["Axis: category"] + S.TECHS, rows, widths=[2.0, 0.8, 0.8, 0.8, 0.9, 1.0], size=8.5, caption="Table 8 - Capability matrix, categorical axes (value for the category the user selects)")
bullets(d, [("Requirement mapping. ", "Data rate (kbps): <=2 ->1, <=50 ->2, <=500 ->3, <=5000 ->4, else 5. Battery (years): <=0.5 ->1, <=2 ->2, <=5 ->3, <=10 ->4, else 5. Cost sensitivity = 1 + device-count tier (<100, <10 000, more: 0/1/2) + budget tier (high/mid/low: 0/1/2). Coverage, mobility and infrastructure are categorical."),
            ("Per-axis suitability. ", "Ordinal axes: 1 - shortfall/4 where shortfall = max(0, requirement - capability); surplus is not rewarded. Categorical axes: matrix value / 5."),
            ("Weights (adjustable, --weights). ", "coverage 1.5, data rate 1.0, battery 1.0, mobility 1.0, infrastructure 0.8, cost 0.8; coverage is highest because a technology that cannot reach the device is useless."),
            ("Rules. ", "R1 data-rate shortfall >= 2 levels: x0.6. R2 coverage capability <= 1: x0.3 and flagged infeasible. R3 wide-area or global mobility with LoRaWAN or BLE/Zigbee (no cellular handover): x0.6. R4 cost sensitivity >= 4 and an operator network not required: +8 for LoRaWAN and BLE/Zigbee (no per-device fees), -8 for subscription technologies. R5 >10-year battery target with RedCap: x0.7.")])
h(d, "3.2 Results", 2)
shot("4_2_selector_S1_S2.png", "Screenshot 12 - iot_selector.py output for scenarios S1 and S2", 6.5)
shot("4_2_selector_summary.png", "Screenshot 13 - summary of all five scenarios", 5.6)
rr = rd(B + "/results/ranked_results.csv")
scs = []
for r in rr:
    if r["scenario"] not in scs: scs.append(r["scenario"])
rows = []
for s in scs:
    top = [r for r in rr if r["scenario"] == s][:3]
    exp = top[0]["expected_top"]
    rows.append([s, f"{top[0]['tech']} ({top[0]['score']})", f"{top[1]['tech']} ({top[1]['score']})", f"{top[2]['tech']} ({top[2]['score']})", "match" if top[0]["tech"] == exp else "diverges"])
table(d, ["Scenario", "1st", "2nd", "3rd", "vs expected"], rows, widths=[2.2, 1.2, 1.2, 1.2, 0.8], size=8.5, caption="Table 9 - Ranked recommendations (scores 0-100)")
para(d, "The first four rows are the Section 4.3 scenarios (water meter, container, factory floor, wearable); their parameters are my reading of the scenario descriptions, so compare them with the unit text. Results: water meter -> NB-IoT (deep indoor, 15-year battery, stationary, operator network); container -> LTE-M (global roaming and mobility; NB-IoT is penalised for weak mobility); factory floor and wearable -> BLE/Zigbee (short range, owned infrastructure). "
        "Divergence note for the container: no terrestrial network exists mid-ocean, so every ranked option needs satellite (NTN) backhaul for that leg; this is stated in the scenario note printed by the tool. "
        "New scenario N1 (10 000 in-ground smart-parking sensors, 20 B per event, 7-year battery, city-wide, operator network, tight budget): NB-IoT 93.4 > LTE-M 90.2 > LoRaWAN 81.6 > RedCap 70.5 > BLE/Zigbee 19.5 (infeasible). The cost pressure favours cheap modules but the operator-network preference blocks the +8 LoRaWAN bonus, so NB-IoT wins on coverage depth and battery.")
para(d, "Limitations: ordinal scores are coarse and the weights are judgement; S3 and S4 tie at the top because both reduce to short-range requirements. The tool is meant to document and audit reasoning, not to replace a link-budget analysis (Project 4.1).")

# ======================================================== 4.3
d.add_page_break()
h(d, "4. Mini Project 4.3 - Multi-sensor MQTT monitoring dashboard")
h(d, "4.1 Design", 2)
table(d, ["Topic", "Publisher", "Interval", "QoS", "Extras"],
      [["plant1/lineA/temperature", "plant_sensor.py --kind temperature", "1.0 s", "1", "LWT on plant1/lineA/status, retained readings"],
       ["plant1/lineA/vibration", "plant_sensor.py --kind vibration", "0.5 s", "1", "retained readings"],
       ["plant1/lineB/temperature", "plant_sensor.py --kind temperature", "1.5 s", "1", "LWT on plant1/lineB/status; the one killed with kill -9"],
       ["plant1/lineB/vibration", "added at t = 20 s while running", "0.7 s", "1", "not known to any subscriber beforehand"]],
      widths=[1.8, 2.0, 0.7, 0.4, 2.0], size=8.5, caption="Table 10 - Topic hierarchy and sensors")
bullets(d, [("aggregator.py: ", "one wildcard subscription plant1/+/+ (QoS 1); timestamps every reading into readings_log.csv and memory (dict keyed by topic); prints a latest-value-per-topic summary periodically; announces each newly discovered topic."),
            ("alert_subscriber.py: ", "independent per-topic thresholds: temperature 85, vibration 4.5, humidity 65, with a per-topic override (lineB temperature 80); it also reports LWT 'offline' events."),
            ("run_demo.py: ", "t=0 start all; t=14 start a late aggregator (retained demo); t=20 add lineB/vibration (new topic demo); t=30 kill -9 the lineB temperature sensor (LWT demo).")])
h(d, "4.2 Results", 2)
shot("4_3_A_aggregator_summary.png", "Screenshot 14 - aggregator: single wildcard subscription, new-topic discovery and periodic summary")
shot("4_3_B_alerts.png", "Screenshot 15 - alert subscriber: per-topic thresholds (vibration 4.5, lineB temperature 80, lineA temperature 85)")
shot("4_3_C_retained_late_joiner.png", "Screenshot 16 - late-joining aggregator: retained last-known values and statuses delivered immediately")
shot("4_3_D_new_topic_no_code_change.png", "Screenshot 17 - new topic plant1/lineB/vibration is picked up by both running aggregators without any code change")
shot("4_3_E_lwt.png", "Screenshot 18 - kill -9 of the lineB temperature sensor: the broker publishes the LWT, aggregator and alert subscriber report 'offline'")
import csv as _c
n = sum(1 for _ in open(os.path.join(R, C, "readings_log.csv"))) - 1
para(d, f"The sample log readings_log.csv contains {n} timestamped readings from the main aggregator; readings_log_late.csv is the late joiner's log, whose first rows carry retained=1.")
h(d, "4.3 Report: publish/subscribe versus request/response", 2)
rep = ("In this system three sensors and three subscribers share one broker, and every participant needs only one connection to it. A publisher sends each reading once to a topic and never learns who listens. When a fourth sensor, plant1/lineB/vibration, was started while everything ran, the aggregator's wildcard subscription picked it up immediately and the alert subscriber applied the vibration threshold with no code or configuration change. "
       "In a request/response design the consumer must know each server's address and poll it, so adding a sensor means reconfiguring every consumer. The scaling difference is structural. With S sensors and C consumers, publish/subscribe needs S + C connections and S publishes per sampling round; HTTP polling needs S x C client-server pairs and S x C requests per round, most of them returning unchanged data. "
       "For 100 sensors and 5 consumers that is 105 connections versus 500; for 1000 sensors and 20 consumers, 1020 versus 20 000. CoAP Observe reduces the polling but the constrained sensor must keep state for every observer, so its load still grows with C, whereas an MQTT sensor's load is independent of how many consumers exist. "
       "Quality of service lets each flow choose its cost: QoS 0 suits high-rate vibration where an occasional loss is harmless, QoS 1 (used here) suits temperature and alarms at the price of possible duplicates, and QoS 2 gives exactly-once delivery through a four-packet handshake. Our experiments show the limits: QoS 1 delivered every reading across a three-second broker outage while QoS 0 lost about 20 per run, but QoS applies hop by hop and cannot save a message from a publisher that dies before transmitting. "
       "Retained messages remove the polling that a request/response consumer needs just to learn the current state. The restarted aggregator received the last value of every topic and both line statuses within 42 ms of connecting, instead of waiting for the next publish or sending a request to each sensor. A retained value can be stale, so status must accompany it. "
       "The Last Will converts silence into an event. When the lineB temperature sensor was killed with SIGKILL, the broker published 'offline' the moment it saw the connection close and the sensor executed no code; a polling client would only discover the failure after a timeout on its next request, and could not distinguish a dead sensor from a slow one. "
       "Adding consumers is just as cheap as adding sensors. The late aggregator was started mid-run while three sensors were publishing, and not one publisher script, topic or log line changed; each sensor still sent exactly one message per reading and the broker did the fan-out. In a polling design every new dashboard adds a full set of requests to every sensor, so a battery-powered device spends more energy and a constrained server may be overloaded by its own monitoring. "
       "Topics also give a natural place for policy: access rules, thresholds and retention can be attached to the hierarchy (plant1/lineA/+) rather than to individual device addresses, as the per-topic alert limits here illustrate. "
       "The trade-offs are real. The broker is a central point of failure and bottleneck that must be clustered or bridged; request/response is simpler, stateless, easily cached and the right pattern when a caller needs a direct answer or must send a command and confirm it. For many-to-many telemetry, however, the broker-mediated pattern keeps connection count and sensor workload nearly constant as sensors and consumers are added, which is why it scales more gracefully.")
para(d, rep); assert 500 <= words(rep) <= 800, words(rep)
para(d, f"(Report length: {words(rep)} words.)", italic=True, size=9)
h(d, "5. Conclusions")
bullets(d, ["MQTT decouples publishers from subscribers in space (no addresses), time (retained messages) and presence (Last Will); each QoS level is a per-hop guarantee, not an end-to-end one.",
            "For the farm scenario LoRaWAN is the only option that satisfies coverage (no operator network), the 5-year battery target and the no-per-device-fee preference; the choice is insensitive to the path-loss exponent.",
            "A transparent weighted-score selector reproduces the worked scenarios and documents why each technology ranks where it does."])
h(d, "Appendix A - Deliverables checklist", 1)
table(d, ["Requirement", "Where"],
      [["4.1 three Part A scripts + logs: normal operation, retained late subscriber, LWT", "mp4_1_mqtt_linkbudget/ ; Screenshots 1-5"],
       ["4.1 Part B script, comparison table, justification paragraph", "link_budget_compare.py ; Table 5, Recommendation"],
       ["4.2 selector, methodology write-up, results for 4 + 1 scenarios", "mp4_2_iot_selector/ ; Section 3"],
       ["4.3 publisher/aggregator/alert scripts, sample log (normal, retained, LWT), 500-800 word report", "mp4_3_mqtt_dashboard/ ; Section 4"]],
      widths=[4.3, 2.5], size=9)
d.add_page_break()
h(d, "Appendix B - Source code", 1)
files = [(A, ["mqtt_common.py", "sensor_publisher.py", "dashboard_subscriber.py", "alert_subscriber.py", "run_partA_demo.py", "crash_publisher.py", "labtask2_qos_crash.py", "lab3_publisher.py", "lab3_subscriber.py", "labtask3_outage.py", "link_budget_compare.py"]),
         (B, ["iot_selector.py"]), (C, ["plant_sensor.py", "aggregator.py", "alert_subscriber.py", "run_demo.py"])]
for sub, fl in files:
    for fn in fl:
        h(d, f"{sub}/{fn}", 3)
        code_block(d, open(os.path.join(R, sub, fn)).read())
out = os.path.join(R, "report", "MC_Unit4_Lab_Report.docx")
d.save(out); print("saved", out)
