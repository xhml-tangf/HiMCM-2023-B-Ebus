"""Generate the conditional Vancouver scenario figure and LaTeX table."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    result = json.loads((ROOT / "results/vancouver_transition_scenarios.json").read_text())
    plt.rcParams.update({"font.size": 12, "axes.titlesize": 12, "axes.spines.top": False,
                         "axes.spines.right": False, "font.family": "DejaVu Sans"})
    fig, axes = plt.subplots(1, 2, figsize=(6.7, 4.2), constrained_layout=True)
    labels, totals = [], []
    base = next(x for x in result["economics"] if x["case"] == "central")
    labels.append("Baseline\nrenewal")
    totals.append(base["baseline_gross_pv_cad"] / 1e9)
    for name, label in [("central", "Electric\nbase"), ("high", "Electric\nhigh")]:
        case = next(x for x in result["economics"] if x["case"] == name)
        labels.append(label)
        totals.append(case["plan_gross_pv_cad"] / 1e9)
    x = np.arange(len(labels))
    ax = axes[0]
    ax.bar(x, totals, color=["#6d7f8c", "#167a8b", "#bd5c27"])
    for xx, value in zip(x, totals):
        ax.text(xx, value + .15, f"{value:.2f}", ha="center")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Gross PV cost (CAD bn)")
    ax.set_title("Project cost to 2033")
    ax.set_ylim(0, max(totals) * 1.13)
    ax.grid(axis="y", alpha=.2)
    ax = axes[1]
    for name, color, label in [("central", "#167a8b", "Base plan"), ("high", "#bd5c27", "High plan")]:
        case = next(x for x in result["economics"] if x["case"] == name)
        grants = case["grant_cases"]
        ax.plot([100 * g["grant_fraction"] for g in grants],
                [g["agency_economic_score_vs_baseline_pct"] for g in grants],
                marker="o", color=color, label=label)
    env = result["environment"]
    ax.text(3, 70,
            f"environment score\n{min(x['environment_score_boundary_pct'] for x in env):.0f}-{max(x['environment_score_boundary_pct'] for x in env):.0f}%",
            va="center", fontsize=10,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#7aa6a0"})
    ax.axhline(0, color="black", linewidth=.7)
    ax.set(xlabel="External grant share (%)", ylabel="Economic score (%)",
           title="Scores and grants")
    ax.set_ylim(min(g["agency_economic_score_vs_baseline_pct"] for c in result["economics"] for g in c["grant_cases"]) - 10,
                max(x["environment_score_boundary_pct"] for x in env) + 8)
    ax.grid(axis="y", alpha=.2)
    ax.legend(frameon=False, loc="lower right")
    fig.savefig(ROOT / "paper/figures/vancouver_transition_scenarios.png", dpi=240)
    plt.close(fig)
    base = next(x for x in result["economics"] if x["case"] == "central")
    high = next(x for x in result["economics"] if x["case"] == "high")
    rows = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{@{}lrr@{}}",
            r"\toprule", r"Scenario & Gross PV (CAD bn) & Score (\%) \\", r"\midrule"]
    rows.append(f"Conventional renewal & {base['baseline_gross_pv_cad']/1e9:.3f} & 0\\\\")
    for name, case in [("Electric, base infrastructure", base), ("Electric, screening high", high)]:
        rows.append(f"{name} & {case['plan_gross_pv_cad']/1e9:.3f} & {case['economic_score_gross_pct']:.1f}\\\\")
    rows += [r"\midrule", r"\multicolumn{3}{@{}l@{}}{Agency PV and score, grants 0/25/50\% (base plan)}\\",
             f"& {base['grant_cases'][0]['agency_pv_cad']/1e9:.3f} / {base['grant_cases'][1]['agency_pv_cad']/1e9:.3f} / {base['grant_cases'][2]['agency_pv_cad']/1e9:.3f} & "
             f"{base['grant_cases'][0]['agency_economic_score_vs_baseline_pct']:.1f} / {base['grant_cases'][1]['agency_economic_score_vs_baseline_pct']:.1f} / {base['grant_cases'][2]['agency_economic_score_vs_baseline_pct']:.1f}\\\\",
             r"\bottomrule", r"\end{tabular}", r"\caption{Conditional generic non-deck case. The 1,741 sequential duty requests are scaled to a derived 1,406-bus non-double-deck, non-trolley fleet under a 300-km range, giving 1,630 battery positions and 1,612 net purchases after 18 delivered BEBs. This is price-mixed screening arithmetic, not a constant-dollar bid appraisal. The 57 double-deck buses and 262 trolleys are outside this sub-boundary; the class-specific result adds them separately. The baseline renews 10/17 of unknown-age fossil positions, and vehicle residual follows a 17-year life.}", r"\end{table}"]
    (ROOT / "paper/tables/vancouver_transition_scenarios.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")
    env_rows = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{@{}lrrrr@{}}",
                r"\toprule", r"Baseline operating mix & g CO$_2$e/km & Renewal (kt) & Electric (kt) & Score (\%)\\",
                r"\midrule"]
    for case in result["environment"]:
        env_rows.append(f"{case['case'].replace('_', ' ')} & {case['baseline_operating_g_per_km']:.0f} & "
                        f"{case['baseline_lifecycle_boundary_t']/1000:.1f} & "
                        f"{case['plan_lifecycle_boundary_t']/1000:.1f} & "
                        f"{case['environment_score_boundary_pct']:.1f}\\\\")
    env_rows += [r"\bottomrule", r"\end{tabular}",
             r"\caption{Conditional generic non-deck ten-year emissions over the named boundary: vehicle and battery production, operating energy, and maintenance. Depot/charging construction and end-of-life credits are excluded. The renewable mix assumes 80\% renewable-diesel reduction plus 96\% RNG for CNG; RNG-heavy uses RNG but fossil diesel; weighted mix uses the 2020 propulsion mix. This is a separate boundary from the class-specific result.}", r"\end{table}"]
    (ROOT / "paper/tables/vancouver_environment_scenarios.tex").write_text("\n".join(env_rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
