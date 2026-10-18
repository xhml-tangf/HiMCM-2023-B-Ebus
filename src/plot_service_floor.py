"""Make the manuscript's conditional 2023-service-floor comparison figure."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with (ROOT / "data/processed/translink_2025_investment_bus_hours.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    years = [int(row["year"]) for row in rows]
    hours_m = [int(row["planned_bus_service_hours_thousands"]) / 1000 for row in rows]
    actual = json.loads((ROOT / "results/actual_service_audit.json").read_text(
        encoding="utf-8"
    ))["bus_totals"]["service_hours"] / 1_000_000
    plt.rcParams.update({"font.size": 12})
    fig, ax = plt.subplots(figsize=(6.5, 3.4), constrained_layout=True)
    ax.plot(years, hours_m, color="#146C94", lw=2.2, marker="o", ms=4.7,
            label="Later bus-hour plan (2025)")
    ax.axhline(actual, color="#B3541E", lw=1.8, ls="--",
               label="2023 actual bus-service floor")
    idx = years.index(2033)
    ax.annotate("1.152 million hours below\n2023 actual (conditional)",
                xy=(2033, hours_m[idx]), xytext=(2029.8, 5.05),
                arrowprops={"arrowstyle": "->", "color": "#333333", "lw": 1},
                fontsize=12, ha="center")
    ax.set(xlim=(2024.6, 2034.4), ylim=(3.9, 7.0),
           xticks=[2025, 2027, 2029, 2031, 2033], ylabel="Annual service (million bus hours)")
    ax.grid(axis="y", color="#dddddd", lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper right", frameon=False, fontsize=12)
    output = ROOT / "paper/figures/service_floor.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
