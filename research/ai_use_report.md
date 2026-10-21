# AI use record

This record maps user requests to retained artifacts. It does not reproduce private chat logs. The final PDF's Report on Use of AI summarizes the same uses.

## Tools

- OpenAI Codex, GPT-6: project planning, independent-source research, modelling, implementation review, manuscript construction and LaTeX checks.
- deepseek-flash: continuation sessions covering GTFS recovery, model audit, conditional scenario implementation and manuscript integration.

Neither tool was asked to locate or use an original 2023 HiMCM solution submission.

## Query themes and retained outputs

1. "Plan the 2023 HiMCM Problem B study, then implement a reproducible paper." Outputs: paper/ebus_transition.tex, src/, tests/, and the repository history.
2. "Search independent electric-bus, fleet planning, route scheduling, infrastructure and mathematical-modelling literature without using the 2023 solution." Outputs: research/literature_and_transfer.md and cited methods in the paper.
3. "Resolve costs, infrastructure, service preservation, fleet parameters and data availability." Outputs: research/parameter_ledger.md, results/cpu_reference_scores.json, and research/cpu_reference_score_note.md.
4. "Use LaTeX and an Outstanding-paper-like format." Output: paper/ebus_transition.tex, research/format_basis.md, compiled PDF, and format/layout checks.
5. "Run CPU algorithms and obtain concrete scores." Outputs: results/charging_tariff_bounds.json, results/london_cohort_roadmap.json, results/cta_2023_detail_audit.json, and results/vancouver_transition_scenarios.json.
6. "Fill missing data rather than leave uncertain gaps." Output: recovered fall-2023 GTFS provenance and audits in data/processed/vancouver_gtfs_2023_provenance.json, results/vancouver_gtfs_baseline_audit.json, and results/vancouver_block_range_audit.json.
7. "Create and upload the private GitHub repository." Output: https://github.com/xhml-tangf/HiMCM-2023-B-Ebus.
8. "Fill the missing official fleet, double-deck/shuttle, regional economic and NOx/PM evidence rather than leaving unexplained gaps." Outputs: `results/apta_2023_fleet_audit.json`, `results/deck_shuttle_electrification_audit.json`, and `results/regional_and_air_quality_audit.json`.
9. "Use the available CPU and run the model, with solution quality first." Outputs: `results/vancouver_transition_uncertainty.json` (432,768 cases), `results/vancouver_full_fleet_bound.json`, and the existing HiGHS/LP runs.
10. "Resolve every issue in the independent adversarial review." Outputs: `research/adversarial_review_resolution.md`, periodic SOC and charger constraints, Route 100 duty sample, asset/infrastructure terminal-value scenarios, Chicago hard-age deadlines, fixed-service sensitivity, CPI rebasing, and a 64-test reproduction suite.
11. "Complete the remaining evidence." Outputs: official TransLink depot, fleet, power and vehicle evidence; the 25-pattern absolute-time city screen; a 275-trolley/5-BEB central split; incremental TCO and infrastructure-inclusive emissions bridges; and body-compatible Chicago/London execution certificates. See `research/remaining_evidence_closure.md` and the current result JSON files.
12. "Restructure the paper around a 90% canonical decision model and remove repeated concessions." Outputs: 15% reserve schedule, driver-relief duty construction, retrofit-first depot model, full-lifecycle score, canonical JSON interface, generated LaTeX values/tables and a rewritten compact manuscript.

## Human-verification boundary

AI-generated text and code were checked through tests, independent formulas, source-page review and compilation. The remaining assumptions are identified in the ledger and paper. The team remains responsible for checking every citation, number and competition-policy statement before submission.
