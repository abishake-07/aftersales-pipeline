"""
Transform raw JSON-Lines tickets → partitioned Parquet (local).

Partitioning by `market` enables Athena partition pruning and
keeps free-tier query scan costs near zero.

Usage:
    python src/transform_to_parquet.py
    python src/transform_to_parquet.py --input data/raw --output data/curated
"""

import argparse
from pathlib import Path

import pandas as pd


def transform(input_dir: str = "data/raw", output_dir: str = "data/curated"):
    input_path = Path(input_dir)
    output_path = Path(output_dir) / "tickets"
    output_path.mkdir(parents=True, exist_ok=True)

    # ── 1. Load all JSON-Lines files ────────────────────────
    jsonl_files = sorted(input_path.glob("*.jsonl"))
    if not jsonl_files:
        print(f"No .jsonl files found in {input_path}")
        return

    dfs = [pd.read_json(f, lines=True) for f in jsonl_files]
    df = pd.concat(dfs, ignore_index=True)
    print(f"Loaded {len(df):,} tickets from {len(jsonl_files)} file(s)")

    # ── 2. Type casting ─────────────────────────────────────
    for col in ("created_at", "updated_at", "resolved_at"):
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")

    df["model_year"] = df["model_year"].astype("int32")
    df["sla_breached"] = df["sla_breached"].astype("bool")

    # ── 3. Write partitioned Parquet (Hive-style) ───────────
    # Creates:  data/curated/tickets/market=DE/part-0.parquet
    #           data/curated/tickets/market=US/part-0.parquet  …
    for market, group in df.groupby("market"):
        market_dir = output_path / f"market={market}"
        market_dir.mkdir(parents=True, exist_ok=True)

        # Drop the partition column from the data file itself
        part = group.drop(columns=["market"])
        out_file = market_dir / "part-0.parquet"
        part.to_parquet(out_file, engine="pyarrow", compression="snappy", index=False)
        print(f"  ✓ {market}: {len(part):,} tickets → {out_file}")

    print(f"\nDone! Parquet files in {output_path}/")
    print(f"Upload with:  aws s3 sync {output_path}/ s3://bmw-aftersales-curated-<ACCOUNT_ID>/tickets/")


def main():
    parser = argparse.ArgumentParser(description="Convert raw JSONL to Parquet.")
    parser.add_argument("--input", default="data/raw", help="Input dir with .jsonl files")
    parser.add_argument("--output", default="data/curated", help="Output base dir")
    args = parser.parse_args()
    transform(args.input, args.output)


if __name__ == "__main__":
    main()
