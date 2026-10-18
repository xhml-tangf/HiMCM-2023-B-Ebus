"""Plot sourced tariff/energy bounds and regenerate the included result table."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    result = json.loads((ROOT / "results/charging_tariff_bounds.json").read_text())
    plt.rcParams.update({"font.size": 12, "axes.titlesize": 12, "axes.spines.top": False,
                         "axes.spines.right": False, "font.family": "DejaVu Sans"})
    hours = np.linspace(4, 12, 81)
    daily_km = 100 * 68000 / 365
    low, high = daily_km * 1.37 / 0.9, daily_km * 2.0 / 0.9
    center = daily_km * 1.6 / 0.9
    fig, axes = plt.subplots(1, 2, figsize=(6.7, 4.1), constrained_layout=True)
    ax = axes[0]
    ax.fill_between(hours, low / hours / 1000, high / hours / 1000, alpha=0.18, color="#167a8b")
    ax.plot(hours, center / hours / 1000, color="#167a8b", label="1.6 kWh/km")
    ax.axhline(5, color="#bd5c27", linestyle="--", label="Assumed 5 MW")
    ax.set(title="Physical power required", xlabel="Charging window (hours)", ylabel="Minimum site power (MW)")
    ax.legend(frameon=False, loc="upper right")
    ax.text(0.04, 0.03, "Band: 1.37–2.0 kWh/km", transform=ax.transAxes)
    ax = axes[1]
    rates = result["central_cases"]
    labels = {"1600": "General\n1600", "1640": "Overnight\n1640", "1650_pre_2026_04": "Transition\npre-Apr 2026"}
    ax.bar([labels[c["rate"]] for c in rates],
           [c["annual_bill_cad_after_rider_before_tax"] / 1e6 for c in rates],
           color=["#6d7f8c", "#167a8b", "#bd5c27"])
    ax.set(title="April-2023 price snapshot", ylabel="Annual bill (CAD million)")
    ax.set_ylim(0, 1.6)
    for i, case in enumerate(rates):
        value = case["annual_bill_cad_after_rider_before_tax"] / 1e6
        ax.text(i, value + 0.04, f"{value:.3f}", ha="center")
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
    fig.savefig(ROOT / "paper/figures/charging_tariff_bounds.png", dpi=240)
    plt.close(fig)
    rows = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{@{}lrrr@{}}",
            r"\toprule", r"Rate & Physical MW & Billed MW & Annual CAD million\\", r"\midrule"]
    for c in rates:
        label = "1650 (pre-Apr 2026)" if c["rate"].startswith("1650") else c["rate"]
        rows.append(f"{label} & {c['physical_peak_kw']/1000:.3f} & {c['billed_peak_kw']/1000:.3f} & "
                    f"{c['annual_bill_cad_after_rider_before_tax']/1e6:.3f}" + r"\\")
    rows += [r"\bottomrule", r"\end{tabular}",
             r"\caption{Conditional charging bounds for 100 distance-equivalent units, "
             r"68,000 km/year each, 1.6 battery-kWh/km, 90\% charging efficiency, "
             r"22:00--06:00 availability and 5-MW site power. "
             r"April-2023 prices are frozen for a 365-day comparison; "
             r"bills include the 1\% rider refund and exclude taxes and capital.}", r"\end{table}"]
    (ROOT / "paper/tables/charging_tariff_bounds.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
