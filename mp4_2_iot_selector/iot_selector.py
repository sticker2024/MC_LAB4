#!/usr/bin/env python3
"""
Mobile Communications - Unit 4 - Mini Project 4.2
Rule-based IoT connectivity technology selector.

Candidates : NB-IoT, LTE-M, LoRaWAN, 5G RedCap, Short-range (BLE/Zigbee)
Axes       : data rate, coverage, battery life, mobility, infrastructure ownership, cost  (Section 4.3)
Method     : (1) capability matrix 0-5 per technology/axis      (transcribed from Sections 4.2/4.3 - see NOTE)
             (2) map the user's requirement onto the same 0-5 scale
             (3) per-axis suitability  s in [0,1]
             (4) weighted sum -> 0-100 match score
             (5) rule-based constraints (multipliers / bonuses / infeasibility flags)
             (6) ranked output with justification naming the axes that drove the ranking

NOTE: the capability numbers below encode typical textbook values (NB-IoT: deep coverage + long battery,
LTE-M: mobility + moderate rate, LoRaWAN: private long-range low-cost, RedCap: high rate / high cost,
BLE-Zigbee: short range, cheapest). If your own Section 4.2/4.3 tables differ, edit the CAPABILITY dict -
nothing else needs to change.

Usage
  python iot_selector.py                       # run the 4 worked scenarios + 1 new scenario
  python iot_selector.py --interactive         # enter a new scenario
  python iot_selector.py --scenario my.json    # scenario from a JSON file
"""
import argparse
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TECHS = ["NB-IoT", "LTE-M", "LoRaWAN", "5G RedCap", "BLE/Zigbee"]

# ------------------------------------------------------------- capability matrix (0-5)
CAPABILITY = {
    "data_rate": {"NB-IoT": 2, "LTE-M": 3, "LoRaWAN": 1, "5G RedCap": 5, "BLE/Zigbee": 3},
    "battery":   {"NB-IoT": 5, "LTE-M": 4, "LoRaWAN": 5, "5G RedCap": 2, "BLE/Zigbee": 4},
    "cost":      {"NB-IoT": 3, "LTE-M": 2, "LoRaWAN": 4, "5G RedCap": 1, "BLE/Zigbee": 5},   # 5 = cheapest at scale
    # categorical axes: value depends on the category the user selects
    "coverage": {
        "deep_indoor":        {"NB-IoT": 5, "LTE-M": 4, "LoRaWAN": 3, "5G RedCap": 2, "BLE/Zigbee": 1},
        "wide_area_cellular": {"NB-IoT": 5, "LTE-M": 5, "LoRaWAN": 3, "5G RedCap": 4, "BLE/Zigbee": 0},
        "long_range_rural":   {"NB-IoT": 2, "LTE-M": 2, "LoRaWAN": 5, "5G RedCap": 1, "BLE/Zigbee": 0},
        "short_range_only":   {"NB-IoT": 1, "LTE-M": 1, "LoRaWAN": 2, "5G RedCap": 1, "BLE/Zigbee": 5},
    },
    "mobility": {
        "stationary":     {"NB-IoT": 5, "LTE-M": 5, "LoRaWAN": 5, "5G RedCap": 4, "BLE/Zigbee": 5},
        "local":          {"NB-IoT": 3, "LTE-M": 4, "LoRaWAN": 3, "5G RedCap": 4, "BLE/Zigbee": 5},
        "wide_area":      {"NB-IoT": 1, "LTE-M": 4, "LoRaWAN": 1, "5G RedCap": 5, "BLE/Zigbee": 0},
        "global_roaming": {"NB-IoT": 1, "LTE-M": 4, "LoRaWAN": 0, "5G RedCap": 4, "BLE/Zigbee": 0},
    },
    "infrastructure": {
        "operator":      {"NB-IoT": 5, "LTE-M": 5, "LoRaWAN": 3, "5G RedCap": 5, "BLE/Zigbee": 1},
        "self_owned":    {"NB-IoT": 1, "LTE-M": 1, "LoRaWAN": 5, "5G RedCap": 2, "BLE/Zigbee": 5},
        "no_preference": {"NB-IoT": 5, "LTE-M": 5, "LoRaWAN": 5, "5G RedCap": 5, "BLE/Zigbee": 5},
    },
}

WEIGHTS = {"data_rate": 1.0, "coverage": 1.5, "battery": 1.0, "mobility": 1.0, "infrastructure": 0.8, "cost": 0.8}
SHORTFALL_DIVISOR = 4.0       # per-level penalty for the ordinal axes (data rate, battery, cost)

# ------------------------------------------------------------- requirement -> 0..5
def data_level(kbps):
    for lim, lvl in ((2, 1), (50, 2), (500, 3), (5000, 4)):
        if kbps <= lim:
            return lvl
    return 5


def battery_level(years):
    for lim, lvl in ((0.5, 1), (2, 2), (5, 3), (10, 4)):
        if years <= lim:
            return lvl
    return 5


def cost_level(device_count, budget):
    c = 0 if device_count < 100 else (1 if device_count < 10000 else 2)
    b = {"high": 0, "mid": 1, "low": 2}[budget]
    return 1 + c + b            # 1 (insensitive) .. 5 (very cost sensitive)


def data_rate_kbps(s):
    if "kbps" in s:
        return s["kbps"]
    return s["msg_bytes"] * 8 / s["interval_s"] / 1000.0


def requirements(s):
    return {"data_rate": data_level(data_rate_kbps(s)), "battery": battery_level(s["battery_years"]),
            "cost": cost_level(s["device_count"], s["budget"]), "coverage": s["coverage"],
            "mobility": s["mobility"], "infrastructure": s["infrastructure"]}


# ------------------------------------------------------------- scoring
def axis_scores(tech, req):
    out = {}
    for a in ("data_rate", "battery", "cost"):
        cap = CAPABILITY[a][tech]
        out[a] = (cap, req[a], max(0.0, 1 - max(0, req[a] - cap) / SHORTFALL_DIVISOR) if a != "cost"
                  else None)
    # cost: capability should be at least as good as the sensitivity requires
    cap, rq = CAPABILITY["cost"][tech], req["cost"]
    out["cost"] = (cap, rq, max(0.0, 1 - max(0, rq - cap) / SHORTFALL_DIVISOR))
    for a in ("coverage", "mobility", "infrastructure"):
        cap = CAPABILITY[a][req[a]][tech]
        out[a] = (cap, 5, cap / 5.0)
    return out


def score_tech(tech, req, scen, weights=WEIGHTS):
    ax = axis_scores(tech, req)
    total_w = sum(weights.values())
    base = 100 * sum(weights[a] * ax[a][2] for a in weights) / total_w
    score, rules, infeasible = base, [], False
    # --- constraint rules
    if req["data_rate"] - CAPABILITY["data_rate"][tech] >= 2:
        score *= 0.6; rules.append("R1 data-rate shortfall >= 2 levels (x0.6)")
    if CAPABILITY["coverage"][req["coverage"]][tech] <= 1:
        score *= 0.3; infeasible = True; rules.append("R2 cannot provide the required coverage type (x0.3, infeasible)")
    if req["mobility"] in ("wide_area", "global_roaming") and tech in ("LoRaWAN", "BLE/Zigbee"):
        score *= 0.6; rules.append("R3 no cellular-style handover for wide-area mobility (x0.6)")
    if req["cost"] >= 4 and scen["infrastructure"] != "operator":
        if tech in ("LoRaWAN", "BLE/Zigbee"):
            score += 8; rules.append("R4 severe cost pressure + self-owned acceptable: no per-device fees (+8)")
        else:
            score -= 8; rules.append("R4 severe cost pressure: per-device subscription/module cost (-8)")
    if req["battery"] == 5 and tech == "5G RedCap":
        score *= 0.7; rules.append("R5 >10-year battery target, RedCap idle power too high (x0.7)")
    return max(0.0, min(100.0, score)), base, ax, rules, infeasible


def justify(tech, ax, rules, infeasible):
    names = {"data_rate": "data rate", "coverage": "coverage", "battery": "battery life",
             "mobility": "mobility", "infrastructure": "infrastructure ownership", "cost": "cost at scale"}
    ranked = sorted(WEIGHTS, key=lambda a: WEIGHTS[a] * ax[a][2], reverse=True)
    strong = [names[a] for a in ranked if ax[a][2] >= 0.9][:3]
    weak = [names[a] for a in sorted(WEIGHTS, key=lambda a: ax[a][2]) if ax[a][2] < 0.7][:2]
    txt = ""
    if strong:
        txt += "Strong on " + ", ".join(strong) + ". "
    if weak:
        txt += "Weak on " + ", ".join(weak) + ". "
    if rules:
        txt += "Rules: " + "; ".join(r.split(" ")[0] for r in rules) + "."
    if infeasible:
        txt += " INFEASIBLE for this scenario."
    return txt.strip()


def rank(scen, weights=WEIGHTS):
    req = requirements(scen)
    rows = []
    for t in TECHS:
        sc, base, ax, rules, inf = score_tech(t, req, scen, weights)
        rows.append({"tech": t, "score": sc, "base": base, "axes": ax, "rules": rules,
                     "infeasible": inf, "why": justify(t, ax, rules, inf)})
    rows.sort(key=lambda r: r["score"], reverse=True)
    return req, rows


def show(scen, weights=WEIGHTS):
    req, rows = rank(scen, weights)
    print("=" * 108)
    print(f"Scenario: {scen['name']}")
    print(f"  {scen.get('description', '')}")
    print(f"  requirement levels -> data_rate {req['data_rate']}/5 ({data_rate_kbps(scen):.4g} kbps), battery {req['battery']}/5 "
          f"({scen['battery_years']} y), cost sensitivity {req['cost']}/5, coverage={req['coverage']}, "
          f"mobility={req['mobility']}, infra={req['infrastructure']}")
    print("-" * 108)
    print(f"{'rank':<5}{'technology':<13}{'score':>7}  justification")
    for i, r in enumerate(rows, 1):
        print(f"{i:<5}{r['tech']:<13}{r['score']:>7.1f}  {r['why']}")
        for ru in r["rules"]:
            print(f"{'':<25}  - {ru}")
    if scen.get("note"):
        print("  NOTE: " + scen["note"])
    return rows


# ------------------------------------------------------------- scenarios
SCENARIOS = [
    dict(name="S1 Smart water meter",
         description="Underground/basement meters, 100 B reading per day, 15-year battery, 50 000 units, operator network.",
         msg_bytes=100, interval_s=86400, battery_years=15, coverage="deep_indoor", mobility="stationary",
         infrastructure="operator", device_count=50000, budget="mid", expected="NB-IoT"),
    dict(name="S2 Fleet-tracked shipping container",
         description="Position report every hour, 200 B, 5-year battery, crosses countries/oceans, 3 000 units.",
         msg_bytes=200, interval_s=3600, battery_years=5, coverage="wide_area_cellular", mobility="global_roaming",
         infrastructure="operator", device_count=3000, budget="mid", expected="LTE-M",
         note="No terrestrial network mid-ocean: any of the five needs satellite/NTN backhaul for the ocean leg - "
              "the tool ranks the terrestrial options only."),
    dict(name="S3 Factory-floor sensor network",
         description="Dense sensors within one building, 200 B every 0.1 s (16 kbps), mains/3-year battery, owned infrastructure.",
         msg_bytes=200, interval_s=0.1, battery_years=3, coverage="short_range_only", mobility="local",
         infrastructure="self_owned", device_count=2000, budget="mid", expected="BLE/Zigbee"),
    dict(name="S4 Wearable health monitor",
         description="Body-worn patch streaming 20 kbps to a phone, rechargeable (days), local mobility.",
         kbps=20, battery_years=0.05, coverage="short_range_only", mobility="local",
         infrastructure="self_owned", device_count=5000, budget="mid", expected="BLE/Zigbee"),
    dict(name="N1 NEW: City smart-parking sensors",
         description="10 000 in-ground sensors, 20 B per event (~every 10 min), 7-year battery, city-wide, operator network, tight budget.",
         msg_bytes=20, interval_s=600, battery_years=7, coverage="wide_area_cellular", mobility="stationary",
         infrastructure="operator", device_count=10000, budget="low", expected="NB-IoT"),
]


def interactive():
    def ask(prompt, choices=None, cast=str):
        while True:
            v = input(prompt + (f" {choices}" if choices else "") + ": ").strip()
            try:
                v = cast(v)
            except ValueError:
                continue
            if not choices or v in choices:
                return v
    return dict(
        name=input("Scenario name: ") or "custom",
        msg_bytes=ask("message size (bytes)", cast=float), interval_s=ask("message interval (seconds)", cast=float),
        battery_years=ask("battery-life target (years)", cast=float),
        coverage=ask("coverage", ["deep_indoor", "wide_area_cellular", "long_range_rural", "short_range_only"]),
        mobility=ask("mobility", ["stationary", "local", "wide_area", "global_roaming"]),
        infrastructure=ask("infrastructure preference", ["operator", "self_owned", "no_preference"]),
        device_count=ask("device count", cast=int), budget=ask("budget tier", ["low", "mid", "high"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--scenario", help="JSON file with one scenario")
    ap.add_argument("--weights", help='JSON string, e.g. \'{"coverage": 2}\' (overrides default weights)')
    a = ap.parse_args()
    w = dict(WEIGHTS)
    if a.weights:
        w.update(json.loads(a.weights))
    if a.interactive:
        show(interactive(), w); return
    if a.scenario:
        show(json.load(open(a.scenario)), w); return
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    table = []
    for s in SCENARIOS:
        rows = show(s, w)
        top = rows[0]["tech"]
        print(f"  => top pick: {top}   (expected from unit reasoning: {s['expected']}) {'MATCH' if top == s['expected'] else 'DIVERGES'}\n")
        for i, r in enumerate(rows, 1):
            table.append({"scenario": s["name"], "rank": i, "tech": r["tech"], "score": round(r["score"], 1),
                          "why": r["why"], "expected_top": s["expected"]})
    with open(os.path.join(HERE, "results", "ranked_results.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(table[0].keys())); wr.writeheader(); wr.writerows(table)
    print("Summary (top 3 per scenario)")
    for s in SCENARIOS:
        t = [r for r in table if r["scenario"] == s["name"]][:3]
        print(f"  {s['name']:<38} " + " > ".join(f"{r['tech']} ({r['score']})" for r in t))


if __name__ == "__main__":
    main()
