"""
Grid connection study: 20 MW solar + 10 MW / 20 MWh battery connecting to a 132 kV grid.

Network:
  132 kV grid (ext grid) -- 132/33 kV transformer -- 33 kV substation bus
      -- 33 kV line (12 km) -- solar farm bus (33 kV): solar 20 MW + battery 10 MW

Studies: load flow (voltage / loading / losses), fault levels, reactive power capability.
Outputs: results_*.csv and voltage_profile.png in the same folder as this script.
All numbers are ASSUMPTIONS for a self-directed project - replace with realistic values.
"""
import os
import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.shortcircuit as sc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))

# ---- assumptions (edit these) ------------------------------------------------
GRID_SC_MVA = 2500.0       # 132 kV grid fault level at the substation (MVA)
SOLAR_MW = 20.0
BATT_MW = 10.0
LINE_KM = 12.0
V_MIN, V_MAX = 0.95, 1.05  # voltage limits (pu) used for the assessment
LINE_MAX_I_KA = 0.45


def build_network():
    net = pp.create_empty_network(name="solar_bess_connection")

    b132 = pp.create_bus(net, vn_kv=132, name="Grid 132kV")
    b33s = pp.create_bus(net, vn_kv=33, name="Substation 33kV")
    b33f = pp.create_bus(net, vn_kv=33, name="Solar farm 33kV")

    pp.create_ext_grid(
        net, bus=b132, vm_pu=1.0, name="Grid",
        s_sc_max_mva=GRID_SC_MVA, s_sc_min_mva=GRID_SC_MVA * 0.6,
        rx_max=0.1, rx_min=0.1,
        x0x_max=1.0, r0x0_max=0.1, x0x_min=1.0, r0x0_min=0.1,  # zero-sequence (earth faults)
    )

    # 132/33 kV, 60 MVA transformer
    pp.create_transformer_from_parameters(
        net, hv_bus=b132, lv_bus=b33s, sn_mva=60, vn_hv_kv=132, vn_lv_kv=33,
        vk_percent=12.0, vkr_percent=0.4, pfe_kw=30, i0_percent=0.1,
        shift_degree=30, tap_side="hv", tap_neutral=0, tap_min=-9, tap_max=9,
        tap_step_percent=1.25, tap_pos=0, name="TX1 132/33kV",
        vector_group="Dyn", vk0_percent=12.0, vkr0_percent=0.4,
        mag0_percent=100.0, mag0_rx=0.0, si0_hv_partial=0.9,  # zero-sequence data
    )

    # 33 kV overhead line / cable to the farm
    pp.create_line_from_parameters(
        net, from_bus=b33s, to_bus=b33f, length_km=LINE_KM,
        r_ohm_per_km=0.13, x_ohm_per_km=0.35, c_nf_per_km=11.0,
        max_i_ka=LINE_MAX_I_KA, name="33kV feeder",
        r0_ohm_per_km=0.4, x0_ohm_per_km=1.0, c0_nf_per_km=11.0,
    )
    net.line["endtemp_degree"] = 80.0  # conductor end temperature for fault calcs

    # generation (positive p_mw = generation for sgen)
    pp.create_sgen(net, b33f, p_mw=SOLAR_MW, q_mvar=0.0, sn_mva=SOLAR_MW / 0.95,
                   name="Solar", type="PV", k=1.1, current_source=True)
    pp.create_sgen(net, b33f, p_mw=0.0, q_mvar=0.0, sn_mva=BATT_MW / 0.95,
                   name="Battery", type="Battery", k=1.1, current_source=True)
    # small auxiliary load at the farm
    pp.create_load(net, b33f, p_mw=0.2, q_mvar=0.05, name="Site aux")
    return net


def set_case(net, solar_mw, batt_mw, q_total_mvar):
    """batt_mw > 0 discharging (export), < 0 charging. q_total split across plant."""
    net.sgen.loc[net.sgen.name == "Solar", ["p_mw", "q_mvar"]] = [solar_mw, q_total_mvar * 0.7]
    net.sgen.loc[net.sgen.name == "Battery", ["p_mw", "q_mvar"]] = [batt_mw, q_total_mvar * 0.3]


def run_case(net, label, solar_mw, batt_mw, q_mvar):
    set_case(net, solar_mw, batt_mw, q_mvar)
    pp.runpp(net, calculate_voltage_angles=True)
    vm = net.res_bus.vm_pu
    row = {
        "case": label,
        "solar_MW": solar_mw, "batt_MW": batt_mw, "Q_MVAr": q_mvar,
        "V_farm_pu": round(vm.iloc[2], 4),
        "V_sub33_pu": round(vm.iloc[1], 4),
        "line_loading_%": round(net.res_line.loading_percent.iloc[0], 1),
        "tx_loading_%": round(net.res_trafo.loading_percent.iloc[0], 1),
        "losses_MW": round(net.res_line.pl_mw.sum() + net.res_trafo.pl_mw.sum(), 3),
        "grid_P_MW": round(-net.res_ext_grid.p_mw.iloc[0], 2),  # + = export to grid
        "grid_Q_MVAr": round(-net.res_ext_grid.q_mvar.iloc[0], 2),
        "voltage_ok": bool(vm.min() >= V_MIN and vm.max() <= V_MAX),
        "thermal_ok": bool(net.res_line.loading_percent.max() <= 100.0
                           and net.res_trafo.loading_percent.max() <= 100.0),
    }
    return row


def load_flow_studies():
    net = build_network()
    cases = [
        ("1 Max solar, battery idle",       SOLAR_MW,  0.0,        0.0),
        ("2 Max solar + battery export",    SOLAR_MW,  BATT_MW,    0.0),
        ("3 Solar charges battery",         SOLAR_MW, -BATT_MW,    0.0),
        ("4 Night, battery export",         0.0,       BATT_MW,    0.0),
        ("5 Night, battery charging",       0.0,      -BATT_MW,    0.0),
        ("6 Max export, absorb 6 MVAr",     SOLAR_MW,  BATT_MW,   -6.0),
        ("7 Max export, supply 6 MVAr",     SOLAR_MW,  BATT_MW,    6.0),
    ]
    rows = [run_case(net, *c) for c in cases]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "results_loadflow.csv"), index=False)
    return net, df


def fault_study(net):
    set_case(net, SOLAR_MW, BATT_MW, 0.0)
    out = {}
    for case in ("max", "min"):
        sc.calc_sc(net, case=case, fault="3ph", ip=True, ith=True)
        out[f"3ph_{case}"] = net.res_bus_sc[["ikss_ka", "ip_ka"]].copy()
    sc.calc_sc(net, case="max", fault="1ph")
    out["1ph_max"] = net.res_bus_sc[["ikss_ka"]].copy()
    rows = []
    for i, name in net.bus.name.items():
        rows.append({
            "bus": name,
            "3ph_max_kA": round(out["3ph_max"].ikss_ka[i], 2),
            "3ph_min_kA": round(out["3ph_min"].ikss_ka[i], 2),
            "peak_ip_kA": round(out["3ph_max"].ip_ka[i], 2),
            "1ph_max_kA": round(out["1ph_max"].ikss_ka[i], 2),
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "results_faultlevels.csv"), index=False)
    return df


def short_circuit_ratio(net):
    """SCR = grid fault level at the connection point / plant rating (weak grid if < ~3)."""
    set_case(net, 0.0, 0.0, 0.0)
    sc.calc_sc(net, case="min", fault="3ph")
    s_sc_mva = np.sqrt(3) * 33.0 * net.res_bus_sc.ikss_ka.iloc[2]
    return s_sc_mva, s_sc_mva / (SOLAR_MW + BATT_MW)


def pq_sweep(net):
    """Farm-bus voltage vs plant Q for full export (shows reactive power capability)."""
    qs = np.linspace(-10, 10, 21)
    v = []
    for q in qs:
        set_case(net, SOLAR_MW, BATT_MW, q)
        pp.runpp(net, calculate_voltage_angles=True)
        v.append(net.res_bus.vm_pu.iloc[2])
    return qs, np.array(v)


def plot_voltage(qs, v):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(qs, v, marker="o")
    ax.axhline(V_MAX, color="r", ls="--", label=f"limit {V_MAX} pu")
    ax.axhline(V_MIN, color="r", ls="--")
    ax.set_xlabel("Plant reactive power (MVAr, + = supplying)")
    ax.set_ylabel("Farm bus voltage (pu)")
    ax.set_title("Voltage vs reactive power at full export (30 MW)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "voltage_profile.png"), dpi=150)


if __name__ == "__main__":
    net, lf = load_flow_studies()
    print("\n=== LOAD FLOW ===")
    print(lf.to_string(index=False))

    fl = fault_study(net)
    print("\n=== FAULT LEVELS ===")
    print(fl.to_string(index=False))

    s_sc, scr = short_circuit_ratio(net)
    print(f"\n=== SCR === fault level at farm bus (min) = {s_sc:.0f} MVA, SCR = {scr:.1f}")

    qs, v = pq_sweep(net)
    plot_voltage(qs, v)
    print("\nSaved: results_loadflow.csv, results_faultlevels.csv, voltage_profile.png")
