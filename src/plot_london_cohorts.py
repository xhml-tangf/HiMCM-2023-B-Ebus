"""Generate the London age-cohort result figure and TeX tables from results."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    results = json.loads((ROOT / "results/london_cohort_roadmap.json").read_text(encoding="utf-8"))
    scenarios = {s["life_cap_years_scenario"]: s for s in results["scenarios"]}
    plt.rcParams.update({"font.size": 12, "axes.titlesize": 12, "axes.spines.top": False,
                         "axes.spines.right": False, "font.family": "DejaVu Sans"})
    fig, axes = plt.subplots(1, 2, figsize=(6.7, 4.2), constrained_layout=True)
    for life, color in [(14, "#bd5c27"), (17, "#167a8b")]:
        rows = scenarios[life]["annual_schedule"]
        years = [r["year"] for r in rows]
        axes[0].plot(years, [r["total_slots_renewed"] for r in rows],
                     marker="o", color=color, label=f"{life}-year life cap")
        axes[1].plot([2023] + years,
                     [7693] + [r["remaining_non_electric_slots"] for r in rows],
                     marker="o", color=color, label=f"{life}-year life cap")
    axes[0].set(title="Annual renewal of\navailable fleet", ylabel="Original fleet positions renewed")
    axes[1].set(title="Original non-electric\nfleet remaining", ylabel="Fleet positions")
    for ax in axes:
        ax.set_xlabel("Year")
        ax.grid(axis="y", alpha=0.2)
        ax.set_xticks([2024, 2028, 2033])
        ax.set_ylim(bottom=0)
    axes[0].legend(frameon=False)
    fig.savefig(ROOT / "paper/figures/london_cohort_roadmap.png", dpi=240)
    plt.close(fig)
    table_dir = ROOT / "paper/tables"
    table_dir.mkdir(exist_ok=True)
    rows = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{@{}rrrr@{}}",
            r"\toprule", r"Life cap & Peak slots/year & Existing EV renewals & Total slots\\",
            r"\midrule"]
    for life, scenario in scenarios.items():
        rows.append(f"{life} & {scenario['minimum_peak_annual_slot_renewal']:,} & "
                    f"{scenario['existing_electric_slots_renewed']:,} & "
                    f"{scenario['total_slots_renewed']:,}" + r"\\")
    rows += [r"\bottomrule", r"\end{tabular}",
             r"\caption{Optimal London fixed-availability cohort benchmarks, 2024--2033. "
             r"Life caps are scenarios. Counts are renewed original fleet slots; "
             r"operational feasibility can require additional buses.}", r"\end{table}"]
    (table_dir / "london_cohort_sensitivity.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")
    rows = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{@{}rrrr@{}}",
            r"\toprule", r"Year & Converted slots & EV renewals & Non-electric slots left\\",
            r"\midrule"]
    for row in scenarios[17]["annual_schedule"]:
        rows.append(f"{row['year']} & {row['non_electric_slots_converted']:,} & "
                    f"{row['existing_electric_slots_renewed']:,} & "
                    f"{row['remaining_non_electric_slots']:,}" + r"\\")
    rows += [r"\bottomrule", r"\end{tabular}",
             r"\caption{An optimal London 17-year-cap fleet-slot roadmap. "
             r"Like-body available slots are maintained; this table does not assign routes or chargers.}",
             r"\end{table}"]
    (table_dir / "london_cohort_annual.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
