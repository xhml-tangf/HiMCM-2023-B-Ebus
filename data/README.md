# Model data

`processed/` contains the cleaned, model-ready GTFS extracts used by `src/claude_*` and the legacy research model. These are derived inputs, not source evidence; their provenance and limitations are recorded under `materials/`.

The two `stop_times.csv.gz` extracts and the full duty replay files are excluded from ordinary Git because they are large. Download the release bundle and run `python scripts/restore_github_assets.py --archive <archive>` to restore them. The summary JSON, final figures, and the LaTeX inputs remain in the repository.
