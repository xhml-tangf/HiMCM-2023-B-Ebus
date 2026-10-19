"""Generate compact tables for the review-closure results."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EOL = "\\\\"


def main() -> None:
    full = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    asset = json.loads((ROOT / "results/vancouver_asset_boundary.json").read_text())
    rows = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{@{}lrrr@{}}",
            r"\toprule", r"Vehicle cost case & Renewal PV & Electric PV & Score (\%)\\",
            r"\midrule"]
    for case in full["economics"]:
        rows.append(f"{case['case'].title()} & {case['baseline_gross_pv_cad']/1e9:.3f} & "
                    f"{case['plan_gross_pv_cad']/1e9:.3f} & "
                    f"{case['economic_score_gross_pct']:.1f}" + EOL)
    cen = next(x for x in full["economics"] if x["case"] == "central")
    grants = cen["grant_cases_symmetric_common_trolley"]
    rows += [r"\midrule",
             r"\multicolumn{4}{@{}l@{}}{Agency score, common trolley grant symmetric in both paths}\\",
             "Grant 0/25/50\\% & & & " + "/".join(
                 f"{g['agency_economic_score_vs_baseline_pct']:.1f}" for g in grants) + EOL,
             r"\bottomrule", r"\end{tabular}",
             r"\caption{Class-specific inventory scenario in constant 2023 CAD (billion; else percent). The electric and renewal paths both include common trolley renewal. The environmental percentage is a scored-conversion subset, while cost includes common trolley capital; the two percentage denominators are therefore different.}",
             r"\end{table}"]
    (ROOT / "paper/tables/vancouver_class_summary.tex").write_text(
        "\n".join(rows) + "\n", encoding="utf-8")

    chosen = [x for x in asset["combined_asset_and_infrastructure_cases"]
              if x["infrastructure_life_years"] in (None, 30)]
    rows = [r"\begin{table}[htbp]", r"\centering",
            r"\begin{tabular}{@{}rrrrr@{}}", r"\toprule",
            r"Sale recovery & Infra life & Renewal PV & Electric PV & Score (\%)\\",
            r"\midrule"]
    for case in chosen:
        infra = "excluded" if case["infrastructure_life_years"] is None else str(case["infrastructure_life_years"])
        rows.append(f"{100*case['market_recovery_fraction']:.0f}\\% & {infra} & "
                    f"{case['baseline_asset_adjusted_pv_cad']/1e9:.3f} & "
                    f"{case['plan_asset_infrastructure_adjusted_pv_cad']/1e9:.3f} & "
                    f"{case['economic_score_pct']:.1f}" + EOL)
    rows += [r"\bottomrule", r"\end{tabular}",
             r"\caption{Asset-boundary cases in billion 2023 CAD. Retained 2023 assets now use the same straight-line life and uniform age assumption in both paths; early conventional retirement receives only the stated share of remaining replacement-cost value. Published infrastructure costs are also shown with a 30-year terminal-value case. These are scenario values, not accounting book values or observed resale bids.}",
             r"\end{table}"]
    (ROOT / "paper/tables/vancouver_asset_boundary.tex").write_text(
        "\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
