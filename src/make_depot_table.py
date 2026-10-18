"""Write the scanned 2025 CMBC depot/profile snapshot and TeX table."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = pd.read_csv(ROOT / "data/processed/cmbc_depot_snapshot_2025.csv")
    assert data.active_buses.sum() == 1733
    assert data.trolley.sum() == 261
    assert data.non_trolley.sum() == 1472
    assert data[["trolley", "hybrid", "cng", "diesel", "gasoline_shuttle", "battery"]].sum(axis=1).eq(data.active_buses).all()
    rows = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{@{}lrrr@{}}", r"\toprule",
            r"Depot & Active & Non-trolley & 50-kW scale (MW)\\ ", r"\midrule"]
    for x in data.itertuples(index=False):
        rows.append(f"{x.depot} & {x.active_buses} & {x.non_trolley} & {x.non_trolley * 0.05:.2f}" + r"\\")
    rows += [r"\midrule", f"Total & {data.active_buses.sum()} & {data.non_trolley.sum()} & {data.non_trolley.sum() * 0.05:.2f}" + r"\\",
             r"\bottomrule", r"\end{tabular}",
             r"\caption{2025-11-18 CMBC active-fleet scale by site. This is retrospective allocation, not 2023 stock; the power column is active non-trolleys times the historical 50-kW planning allowance, not available transformer capacity.}", r"\end{table}"]
    (ROOT / "paper/tables/depot_scale.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
