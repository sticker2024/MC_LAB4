#!/usr/bin/env python3
"""
Mobile Communications - Unit 4 - Mini Project 4.1, Part B
Simplified LPWAN link-budget and battery-life comparison: NB-IoT vs LTE-M (CE Mode B) vs LoRaWAN (SF12)

Scenario (assigned): 200 soil-moisture/temperature sensors over a 25 km^2 farm, 12-byte reading every
30 min, max sensor-to-gateway distance 8 km, 5-year target on a 3.6 V / 19 000 mAh primary lithium cell,
NO cellular coverage nearby, preference to avoid per-device fees at 200-unit scale.

    python link_budget_compare.py              # Part B table (3 technologies)
    python link_budget_compare.py --all        # + lab tasks 4 (container), 5 (RedCap), 6 (path-loss exponent)

Model
  MCL  = P_tx - S_rx                                   (dB)
  PL(d) = PL(d0) + 10 n log10(d/d0),  d0 = 1 km, PL(d0) = 91.5 dB (~900 MHz), n = 3.5 (open rural)
  margin = MCL - PL(d)
  energy per cycle  = I_tx*t_tx + I_rx*t_rx + I_sleep*(T_cycle - t_tx - t_rx)        [mAh]
  life (years)      = capacity / (energy_per_cycle * cycles_per_year)

ALL CURRENT / TIME VALUES ARE REPRESENTATIVE ASSUMPTIONS (typical module datasheet orders of
magnitude), not measurements.  Replace them with the datasheet values of your chosen module.
"""
import argparse
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ scenario
CAPACITY_MAH = 19000.0
CYCLE_S = 30 * 60.0
CYCLES_PER_YEAR = 365 * 24 * 3600 / CYCLE_S        # 17 520
DISTANCE_KM = 8.0
D0_KM, PL_D0 = 1.0, 91.5
N_EXP = 3.5
PAYLOAD_B = 12
TARGET_YEARS = 5.0
SELF_DISCHARGE = 0.01                               # 1 %/year of nominal capacity (primary lithium)
FADE_MARGIN_REQ = 10.0                              # dB we want to keep in hand


def lora_time_on_air(payload_bytes, sf=12, bw=125e3, cr=1, preamble=8, header=True, crc=True):
    """Semtech SX127x time-on-air formula (low-data-rate optimisation on for SF11/12 @125 kHz)."""
    t_sym = (2 ** sf) / bw
    de = 1 if (sf >= 11 and bw <= 125e3) else 0
    h = 0 if header else 1
    num = 8 * payload_bytes - 4 * sf + 28 + 16 * (1 if crc else 0) - 20 * h
    n_payload = 8 + max(math.ceil(num / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return (preamble + 4.25) * t_sym + n_payload * t_sym


LORAWAN_OVERHEAD_B = 13                              # MHDR+DevAddr+FCtrl+FCnt+FPort+MIC
LORA_TOA = lora_time_on_air(PAYLOAD_B + LORAWAN_OVERHEAD_B, sf=12)

TECH = {
    #            P_tx  S_rx    I_tx   t_tx      I_rx  t_rx  I_sleep   note
    "NB-IoT":   dict(p=23, s=-129, i_tx=220, t_tx=3.0,     i_rx=0,  t_rx=0.0, i_sl_uA=3,
                     note="single-tone UL, many repetitions at deep coverage; 3 s active incl. signalling"),
    "LTE-M":    dict(p=23, s=-125, i_tx=300, t_tx=3.0,     i_rx=0,  t_rx=0.0, i_sl_uA=5,
                     note="CE Mode B repetitions; higher peak current than NB-IoT"),
    "LoRaWAN":  dict(p=14, s=-137, i_tx=44,  t_tx=LORA_TOA, i_rx=11, t_rx=0.4, i_sl_uA=2,
                     note=f"SF12/125 kHz, {PAYLOAD_B}+{LORAWAN_OVERHEAD_B} B frame -> {LORA_TOA:.2f} s time-on-air; Class A RX windows 0.4 s"),
}
REDCAP = dict(p=23, s=-94, i_tx=400, t_tx=1.5, i_rx=0, t_rx=0.0, i_sl_uA=50,
              note="NR RedCap, 20 MHz FR1 (representative): sensitivity ~ -94 dBm, 1.5 s active incl. signalling, eDRX idle 50 uA")


# ------------------------------------------------------------------ model
def mcl(t):
    return t["p"] - t["s"]


def path_loss(d_km, n=N_EXP, pl_d0=PL_D0, d0=D0_KM):
    return pl_d0 + 10 * n * math.log10(d_km / d0)


def energy_per_cycle_mAh(t):
    sleep_s = CYCLE_S - t["t_tx"] - t["t_rx"]
    return (t["i_tx"] * t["t_tx"] + t["i_rx"] * t["t_rx"] + t["i_sl_uA"] / 1000.0 * sleep_s) / 3600.0


def life_years(t, self_discharge=0.0):
    annual = energy_per_cycle_mAh(t) * CYCLES_PER_YEAR + self_discharge * CAPACITY_MAH
    return CAPACITY_MAH / annual, annual


def analyse(name, t, n=N_EXP, d=DISTANCE_KM):
    pl = path_loss(d, n)
    margin = mcl(t) - pl
    e = energy_per_cycle_mAh(t)
    yrs, annual = life_years(t)
    yrs_sd, _ = life_years(t, SELF_DISCHARGE)
    return {"tech": name, "tx_dbm": t["p"], "sens_dbm": t["s"], "mcl_db": mcl(t), "pl_db": pl,
            "margin_db": margin, "mah_cycle": e, "mah_year": annual, "years": yrs, "years_incl_selfdischarge": yrs_sd}


def print_table(rows, title):
    print(f"\n{title}")
    print(f"{'technology':<12}{'Ptx':>5}{'Srx':>7}{'MCL':>7}{'PL':>8}{'margin':>8}  {'mAh/cycle':>10}{'mAh/year':>10}"
          f"{'years':>8}{'yrs(+1%SD)':>12}  meets 5 y?")
    for r in rows:
        ok = "yes" if r["years_incl_selfdischarge"] >= TARGET_YEARS else "NO"
        link = "link closes" if r["margin_db"] >= FADE_MARGIN_REQ else ("thin margin" if r["margin_db"] > 0 else "NO LINK")
        print(f"{r['tech']:<12}{r['tx_dbm']:>5}{r['sens_dbm']:>7}{r['mcl_db']:>7.0f}{r['pl_db']:>8.1f}{r['margin_db']:>8.1f}  "
              f"{r['mah_cycle']:>10.4f}{r['mah_year']:>10.0f}{r['years']:>8.1f}{r['years_incl_selfdischarge']:>12.1f}  {ok:<4} ({link})")


def recommend(rows, cellular_coverage=False):
    """Very small decision rule combining the numbers with the Section 4.3 axes."""
    verdict = []
    for r in rows:
        reasons = []
        feasible = True
        if r["margin_db"] < FADE_MARGIN_REQ:
            feasible = False; reasons.append(f"margin {r['margin_db']:.1f} dB < {FADE_MARGIN_REQ:.0f} dB")
        if r["years_incl_selfdischarge"] < TARGET_YEARS:
            feasible = False; reasons.append(f"life {r['years_incl_selfdischarge']:.1f} y < {TARGET_YEARS:.0f} y")
        if r["tech"] in ("NB-IoT", "LTE-M", "5G RedCap") and not cellular_coverage:
            feasible = False; reasons.append("needs operator coverage (none nearby) + per-device subscription")
        verdict.append((r["tech"], feasible, reasons))
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="also run lab tasks 4, 5 and 6")
    ap.add_argument("--n", type=float, default=N_EXP)
    args = ap.parse_args()
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "figures"), exist_ok=True)

    print("=" * 110)
    print("Part B - LPWAN link budget and battery life")
    print(f"scenario: 200 sensors, {PAYLOAD_B} B every {CYCLE_S/60:.0f} min ({CYCLES_PER_YEAR:.0f} cycles/yr), "
          f"d = {DISTANCE_KM:.0f} km, battery {CAPACITY_MAH:.0f} mAh, target {TARGET_YEARS:.0f} y")
    print(f"path loss model: PL(d) = {PL_D0} + 10*{args.n}*log10(d/{D0_KM:.0f} km)  ->  PL({DISTANCE_KM:.0f} km) = {path_loss(DISTANCE_KM, args.n):.1f} dB")
    print(f"LoRaWAN SF12 time-on-air for {PAYLOAD_B + LORAWAN_OVERHEAD_B} B PHY payload = {LORA_TOA*1000:.0f} ms "
          f"-> duty cycle per 30 min = {100*LORA_TOA/CYCLE_S:.3f} % (EU868 limit 1 %)")
    print("=" * 110)
    for k, t in TECH.items():
        print(f"  assumption {k:<8}: Ptx {t['p']} dBm, Srx {t['s']} dBm, I_tx {t['i_tx']} mA x {t['t_tx']:.2f} s, "
              f"I_rx {t['i_rx']} mA x {t['t_rx']} s, sleep {t['i_sl_uA']} uA  [{t['note']}]")
    rows = [analyse(k, t, n=args.n) for k, t in TECH.items()]
    print_table(rows, "Comparison table (Part B)")
    with open(os.path.join(HERE, "results", "partB_comparison.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    print("\nFeasibility verdict (link margin >= 10 dB, life >= 5 y incl. self-discharge, operator coverage required for cellular):")
    for tech, ok, reasons in recommend(rows):
        print(f"  {tech:<8}: {'FEASIBLE' if ok else 'not recommended'}" + ("" if ok else "  - " + "; ".join(reasons)))

    # ---- figure
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    names = [r["tech"] for r in rows]
    a1.bar(names, [r["margin_db"] for r in rows], color=["tab:blue", "tab:orange", "tab:green"])
    a1.axhline(FADE_MARGIN_REQ, color="k", ls=":"); a1.set_ylabel("coverage margin at 8 km (dB)")
    a1.set_title("Link margin (MCL - PL)")
    for i, r in enumerate(rows):
        a1.text(i, r["margin_db"] + 0.5, f"{r['margin_db']:.1f}", ha="center")
    a2.bar(names, [r["years_incl_selfdischarge"] for r in rows], color=["tab:blue", "tab:orange", "tab:green"])
    a2.axhline(TARGET_YEARS, color="r", ls="--", label="5-year target"); a2.set_yscale("log")
    a2.set_ylabel("battery life, years (log)"); a2.set_title("Estimated battery life (19 000 mAh)"); a2.legend()
    for i, r in enumerate(rows):
        a2.text(i, r["years_incl_selfdischarge"] * 1.1, f"{r['years_incl_selfdischarge']:.1f}", ha="center")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "figures", "partB_margin_and_life.png"), dpi=140); plt.close(fig)

    if not args.all:
        return

    # ================= Lab task 4: container, ocean crossing =================
    print("\n" + "=" * 110)
    print("Lab task 4 - fleet-tracked shipping container, ocean crossing (no terrestrial coverage)")
    print("=" * 110)
    print("Margin vs distance from the nearest base station/gateway, same MCLs (n = 3.5, and free-space n = 2 as a best case):")
    print(f"{'distance':>10}{'PL n=3.5':>10}{'PL n=2':>9}" + "".join(f"{k + ' m(n=3.5)':>18}" for k in TECH) + f"{'  best-case(n=2) NB-IoT':>26}")
    for d in (1, 8, 30, 100, 370, 1000, 3000):
        line = f"{d:>8}km{path_loss(d):>10.1f}{path_loss(d, 2.0):>9.1f}"
        for k, t in TECH.items():
            line += f"{mcl(t) - path_loss(d):>18.1f}"
        line += f"{mcl(TECH['NB-IoT']) - path_loss(d, 2.0):>26.1f}"
        print(line)
    print("Distance at which each technology's margin reaches 0 dB (n = 3.5):")
    for k, t in TECH.items():
        d_max = D0_KM * 10 ** ((mcl(t) - PL_D0) / (10 * N_EXP))
        print(f"  {k:<8}: {d_max:7.1f} km")
    print("""
Why one distance cannot justify a technology here:
  * The container moves: its distance to the nearest base station changes continuously from ~0 km in port
    to thousands of km mid-ocean, so a single d (8 km in the farm) is meaningless - the answer is a
    coverage-availability *profile* along the route, not one margin number.
  * Beyond ~50 km from a base station the terrestrial margin is already negative for every technology
    (see table); even with ideal free-space propagation (n = 2) the NB-IoT margin is only ~0 dB at 1000 km,
    before real satellite slant range, pointing loss or Doppler - so no tuning of n, SF or repetitions fixes it.
  * The decision is governed by non-link-budget axes of Section 4.3: roaming agreements / network
    availability, mobility and hand-over, satellite (NTN) access, power/energy per position fix.
  * The link budget would be re-done per segment (port, coastal, deep-sea) and for the satellite link geometry
    (slant range, elevation, antenna gains), not with the terrestrial log-distance model.""")

    # ================= Lab task 5: RedCap =================
    print("=" * 110)
    print("Lab task 5 - add 5G RedCap (representative values)")
    print("=" * 110)
    rows5 = rows + [analyse("5G RedCap", REDCAP, n=args.n)]
    print(f"  assumption 5G RedCap: {REDCAP['note']}")
    print_table(rows5, "Extended comparison table (with RedCap)")
    with open(os.path.join(HERE, "results", "labtask5_with_redcap.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows5[0].keys())); w.writeheader(); w.writerows(rows5)

    # ================= Lab task 6: path-loss exponent =================
    print("=" * 110)
    print("Lab task 6 - sensitivity to the path-loss exponent n")
    print("=" * 110)
    allt = dict(TECH); allt["5G RedCap"] = REDCAP
    print(f"{'n':>5}{'PL(8km)':>9}" + "".join(f"{k:>12}" for k in allt) + "   recommended (feasible set)")
    n_rows = []
    for n in (2.5, 3.0, 3.5, 4.0, 4.5, 5.0):
        rr = [analyse(k, t, n=n) for k, t in allt.items()]
        feas = [tech for tech, ok, _ in recommend(rr) if ok]
        print(f"{n:>5.1f}{path_loss(8, n):>9.1f}" + "".join(f"{r['margin_db']:>12.1f}" for r in rr) +
              f"   {', '.join(feas) if feas else 'none'}")
        for r in rr:
            n_rows.append({"n": n, **r})
    print("\nBreak-even exponent where the 8 km margin drops to the 10 dB reserve / to 0 dB:")
    for k, t in allt.items():
        n10 = (mcl(t) - FADE_MARGIN_REQ - PL_D0) / (10 * math.log10(DISTANCE_KM / D0_KM))
        n0 = (mcl(t) - PL_D0) / (10 * math.log10(DISTANCE_KM / D0_KM))
        print(f"  {k:<10}: n(10 dB) = {n10:5.2f}   n(0 dB) = {n0:5.2f}")
    with open(os.path.join(HERE, "results", "labtask6_exponent_sweep.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(n_rows[0].keys())); w.writeheader(); w.writerows(n_rows)

    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    ns = [2.5 + 0.1 * i for i in range(0, 31)]
    for k, t in allt.items():
        ax.plot(ns, [mcl(t) - path_loss(8, n) for n in ns], label=k)
    ax.axhline(FADE_MARGIN_REQ, color="k", ls=":", label="10 dB reserve"); ax.axhline(0, color="r", lw=1)
    ax.set_xlabel("path-loss exponent n"); ax.set_ylabel("margin at 8 km (dB)")
    ax.set_title("Lab task 6 - margin vs path-loss exponent"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "figures", "labtask6_margin_vs_n.png"), dpi=140); plt.close(fig)


if __name__ == "__main__":
    main()
