# Mobile Communications - Unit 4 Mini Projects (code + lab report)

```
report/MC_Unit4_Lab_Report.docx    <- the lab report (PDF copy alongside), screenshots/figures/tables embedded
mp4_1_mqtt_linkbudget/             Part A MQTT scripts + lab tasks 1-3, Part B link_budget_compare.py (+ tasks 4-6)
mp4_2_iot_selector/                iot_selector.py (rule-based selector)
mp4_3_mqtt_dashboard/              plant_sensor.py, aggregator.py, alert_subscriber.py, run_demo.py
screenshots/                       console screenshots used in the report
tools/                             make_screenshots.py, term_shot.py, report_lib.py
```

## Run (Python 3.9+, Mosquitto broker installed: `sudo apt install mosquitto`)
```
pip install -r requirements.txt
cd mp4_1_mqtt_linkbudget && python run_partA_demo.py      # starts a local broker + all clients, writes logs/
                           python run_lab_tasks.py        # lab tasks 1-3 (takes a few minutes)
                           MODE=ordered python labtask3_outage.py
                           python link_budget_compare.py --all
cd ../mp4_2_iot_selector  && python iot_selector.py       # or --interactive
cd ../mp4_3_mqtt_dashboard && python run_demo.py
```
Manual run (as in the lab): start `mosquitto -c mosquitto_test.conf`, then dashboard_subscriber.py, alert_subscriber.py and
sensor_publisher.py in separate terminals. Use `MQTT_HOST` / `MQTT_PORT` to point at a public test broker instead.

## Things to know
* MQTT results come from a real Mosquitto 2.0.18 broker; demos use 0.5-1.5 s publish intervals (scripts default to the lab's 5 s).
* Part B current/time values and the RedCap sensitivity are representative *assumptions* - replace with datasheet values.
* 4.2: I did not have the manual's Section 4.2/4.3 tables, so the capability matrix and the four scenario parameters
  encode standard values / my reading of the scenarios. Edit CAPABILITY and SCENARIOS in iot_selector.py to match yours.
* The console "screenshots" are images rendered from the real captured logs, not OS screen grabs.
* Fill in your name / ID on the report's title page.
