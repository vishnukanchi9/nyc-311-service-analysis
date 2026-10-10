"""Run every analysis query, save results to outputs/ as CSV and charts to images/.

Usage:
    python src/run_analysis.py            # reuse data/nyc311.duckdb if built
    python src/run_analysis.py --rebuild  # rebuild the staging table from data/raw
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import charts  # noqa: E402
from queries import ROOT, connect, run_file  # noqa: E402

SQL_FILES = ["02_data_quality.sql", "03_demand.sql", "04_performance.sql", "05_equity.sql"]
OUT_DIR = ROOT / "outputs"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    con = connect(rebuild=args.rebuild)
    OUT_DIR.mkdir(exist_ok=True)

    results = {}
    for f in SQL_FILES:
        results.update(run_file(con, f))
    for name, df in results.items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False)
    print(f"Wrote {len(results)} result tables to {OUT_DIR.relative_to(ROOT)}/")

    figures = {
        "01_monthly_volume": charts.monthly_volume(results["monthly_volume"]),
        "02_top_complaints": charts.top_complaints(results["top_complaints"]),
        "03_seasonality": charts.seasonality_heatmap(results["seasonality_top_complaints"]),
        "04_hour_weekday": charts.hour_weekday_heatmap(results["hour_by_weekday"]),
        "05_agency_resolution": charts.agency_resolution(results["agency_performance"]),
        "06_borough_equity": charts.borough_raw_vs_adjusted(results["borough_equity"]),
        "07_district_ranking": charts.district_ranking(results["district_equity"]),
        "08_nypd_core_types": charts.nypd_core_types(results["nypd_core_types_by_borough"]),
    }
    for name, fig in figures.items():
        charts.save(fig, name)
    print(f"Wrote {len(figures)} charts to images/")


if __name__ == "__main__":
    main()
