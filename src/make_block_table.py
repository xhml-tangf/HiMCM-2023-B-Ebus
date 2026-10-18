"""Write the manuscript's actual-block range table from the executed audit."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EOL = "\\\\"


def main() -> None:
    result = json.loads((ROOT / "results/vancouver_block_range_audit.json").read_text())
    weekday = next(x for x in result["days"] if x["kind"] == "weekday")
    rows = ["\\begin{table}[htbp]", "\\centering", "\\begin{tabular}{@{}lrrrrrr@{}}",
            "\\toprule",
            "Proxy & Baseline & \\multicolumn{5}{c}{Additional sequential block requests by range}" + EOL,
            "class & blocks & 150 & 185 & 250 & 300 & 350 km" + EOL, "\\midrule"]
    for scenario, name, ranges in [("40ft", "40-ft battery proxy", [149, 184, 250, 300, 350]),
                                   ("60ft", "60-ft battery proxy", [150, 185, 251, 300, 350])]:
        cases = [x for x in weekday["range_scenarios"] if x["scenario"] == scenario]
        base = cases[0]["battery_candidate_blocks"]
        values = []
        for km in ranges:
            case = next(x for x in cases if x["range_km"] == km)
            values.append(case["fleet_blocks_after_ceiling"] - base)
        rows.append(f"{name} & {base} & " + " & ".join(str(x) for x in values) + EOL)
    rows += ["\\bottomrule", "\\end{tabular}",
             "\\caption{2023-11-14 service with 1,752 published duty blocks and 1,087 simultaneous trips. Capacity signatures are route-level proxies, not observed bus assignments. The 40-ft battery proxy contains minimum/standard capacity classes and 216 unclassified blocks; 47/70-seat signature blocks are retained only as a trolley-route proxy, and 85-person double-deck blocks are unassessed. Counts are daily sequential block requests, not a garage fleet or one-for-one bus count.}", "\\end{table}"]
    (ROOT / "paper/tables/block_range_stress.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
