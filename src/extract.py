"""Extract one year of NYC 311 service requests from the NYC Open Data (Socrata) API.

Pulls only the columns the analysis needs, one month at a time, and writes each
month to a Parquet file under data/raw/. Re-running skips months already on disk.

Usage:
    python src/extract.py --year 2025
"""

from __future__ import annotations

import argparse
import io
import time
from pathlib import Path

import pandas as pd
import requests

ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"
PAGE_SIZE = 250_000
COLUMNS = [
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "complaint_type",
    "descriptor",
    "status",
    "incident_zip",
    "borough",
    "community_board",
    "open_data_channel_type",
    "latitude",
    "longitude",
]
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def fetch_page(where: str, offset: int, retries: int = 5) -> pd.DataFrame:
    params = {
        "$select": ",".join(COLUMNS),
        "$where": where,
        "$order": "unique_key",
        "$limit": PAGE_SIZE,
        "$offset": offset,
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(ENDPOINT, params=params, timeout=300)
            resp.raise_for_status()
            return pd.read_csv(io.StringIO(resp.text), dtype=str)
        except (requests.RequestException, pd.errors.ParserError) as exc:
            wait = 2**attempt
            print(f"    attempt {attempt} failed ({exc}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Giving up on offset {offset} for {where}")


def extract_month(year: int, month: int) -> None:
    out = RAW_DIR / f"311_{year}_{month:02d}.parquet"
    if out.exists():
        print(f"{out.name} already exists, skipping")
        return

    start = f"{year}-{month:02d}-01T00:00:00"
    end = f"{year + (month == 12)}-{month % 12 + 1:02d}-01T00:00:00"
    where = f"created_date >= '{start}' AND created_date < '{end}'"

    pages, offset = [], 0
    while True:
        page = fetch_page(where, offset)
        pages.append(page)
        print(f"  {year}-{month:02d}: fetched {offset + len(page):,} rows")
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    df = pd.concat(pages, ignore_index=True)
    df.to_parquet(out, index=False)
    print(f"Wrote {len(df):,} rows to {out.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for month in range(1, 13):
        extract_month(args.year, month)


if __name__ == "__main__":
    main()
