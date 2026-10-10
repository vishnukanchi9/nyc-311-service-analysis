"""Load the SQL files in sql/ into a DuckDB database and run named queries.

Each SQL file is split on `-- name: <query_name>` markers. Unnamed leading
statements and DDL (CREATE ...) are executed; named SELECTs are returned as
pandas DataFrames.
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
DB_PATH = ROOT / "data" / "nyc311.duckdb"

_NAME_RE = re.compile(r"^--\s*name:\s*(\w+)\s*$", re.MULTILINE)


def connect(rebuild: bool = False) -> duckdb.DuckDBPyConnection:
    """Open the analysis database, building the staging table if needed."""
    con = duckdb.connect(str(DB_PATH))
    # read_parquet paths in the SQL are relative to the project root
    con.execute(f"SET file_search_path = '{ROOT.as_posix()}'")
    has_table = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'stg_requests'"
    ).fetchone()[0]
    if rebuild or not has_table:
        con.execute((SQL_DIR / "01_staging.sql").read_text())
    return con


def load_queries(filename: str) -> dict[str, str]:
    text = (SQL_DIR / filename).read_text()
    parts = _NAME_RE.split(text)
    # parts = [preamble, name1, body1, name2, body2, ...]
    return {name: body.strip().rstrip(";") for name, body in zip(parts[1::2], parts[2::2])}


def run_file(con: duckdb.DuckDBPyConnection, filename: str) -> dict[str, pd.DataFrame]:
    """Run every named query in a file, in order. DDL is executed, SELECTs returned."""
    results = {}
    for name, sql in load_queries(filename).items():
        body = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--")).strip()
        if body.upper().startswith("CREATE"):
            con.execute(sql)
        else:
            results[name] = con.execute(sql).df()
    return results
