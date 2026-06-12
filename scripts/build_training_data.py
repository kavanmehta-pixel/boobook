#!/usr/bin/env python3
"""
Boobook training data pipeline.
Downloads/processes AIS datasets and runs anomaly detection.

Usage:
    python scripts/build_training_data.py --source noaa
    python scripts/build_training_data.py --source noaa --bbox australia_wide
    python scripts/build_training_data.py --source amsa --amsa-file data/amsa.csv --bbox torres_strait
"""
from __future__ import annotations
import argparse, logging, sys, zipfile
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from boobook.ingest.noaa_ais import load_noaa_csv
from boobook.ingest.amsa_cts import normalise_file
from boobook.analytics.ais_anomaly import run_validation

BBOXES = {
    "torres_strait":  (141.0, -11.5, 144.5,  -8.5),
    "arafura":        (130.0, -13.0, 138.0,  -8.0),
    "darwin":         (129.0, -13.5, 132.0, -11.0),
    "australia_wide": ( 95.0, -48.0, 170.0,  -4.0),
}

NOAA_URL = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2023/AIS_2023_01_01.zip"


def _download(url, dest):
    import urllib.request
    if Path(dest).exists():
        log.info("Cached: %s", Path(dest).name); return True
    log.info("Downloading %s ...", url)
    try:
        urllib.request.urlretrieve(url, dest)
        log.info("OK %.1f MB", Path(dest).stat().st_size/1e6); return True
    except Exception as e:
        log.error("Download failed: %s", e); return False


def print_summary(source, df, alerts_df):
    print(f"\n{'='*60}")
    print(f"  Source  : {source}")
    print(f"  Vessels : {df['mmsi'].nunique():,}")
    print(f"  AIS rows: {len(df):,}")
    print(f"  Alerts  : {len(alerts_df):,}")
    if not alerts_df.empty and "severity" in alerts_df.columns:
        sev = alerts_df["severity"].value_counts()
        for s in ["HIGH","MEDIUM","LOW"]:
            print(f"    {s:6}: {sev.get(s,0)}")
    if not alerts_df.empty and "alert_type" in alerts_df.columns:
        print("\n  Alert types:")
        for t, n in alerts_df["alert_type"].value_counts().items():
            print(f"    {t}: {n}")
    if not alerts_df.empty:
        cols = [c for c in ["vessel_name","vessel_type","alert_type","risk_score","severity"] if c in alerts_df.columns]
        print("\n  Top 10 by risk score:")
        score_col = "risk_score" if "risk_score" in alerts_df.columns else "score"
        print(alerts_df.nlargest(min(10,len(alerts_df)), score_col)[cols].to_string(index=False))
    print()


def run_noaa(out_dir: Path, bbox_name: str | None):
    raw_dir = Path("data/noaa_raw"); raw_dir.mkdir(parents=True, exist_ok=True)
    bbox = BBOXES.get(bbox_name) if bbox_name else None

    existing_csvs = list(raw_dir.glob("*.csv"))
    if existing_csvs:
        csv_path = existing_csvs[0]
        log.info("Using cached: %s", csv_path.name)
    else:
        zip_path = raw_dir / "noaa_2023_01_01.zip"
        if not _download(NOAA_URL, zip_path): return
        with zipfile.ZipFile(zip_path) as zf: zf.extractall(raw_dir)
        csv_path = list(raw_dir.glob("*.csv"))[0]

    df = load_noaa_csv(csv_path, bbox=bbox)
    if df.empty:
        log.warning("No data after filtering — try a different bbox"); return

    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"noaa_2023-01-01_{bbox_name or 'global'}"
    df.to_csv(out_dir / f"{tag}_tracks.csv", index=False)

    log.info("Running anomaly detection on %d rows...", len(df))
    alerts_df, _, _, stats = run_validation(df)
    print_summary(f"NOAA 2023-01-01 [{bbox_name or 'global'}]", df, alerts_df)

    if not alerts_df.empty:
        alerts_df.to_csv(out_dir / f"{tag}_alerts.csv", index=False)
        log.info("Saved → %s", out_dir / f"{tag}_alerts.csv")


def run_amsa(amsa_file: str, out_dir: Path, bbox_name: str | None):
    df = normalise_file(amsa_file)
    if bbox_name and bbox_name in BBOXES:
        lo, la, hi, ha = BBOXES[bbox_name]
        df = df[df["lon"].between(lo, hi) & df["lat"].between(la, ha)]
        log.info("After bbox clip: %d rows", len(df))

    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"amsa_{bbox_name or 'australia'}"
    df.to_csv(out_dir / f"{tag}_tracks.csv", index=False)

    alerts_df, _, _, stats = run_validation(df)
    print_summary(f"AMSA [{bbox_name or 'australia'}]", df, alerts_df)
    if not alerts_df.empty:
        alerts_df.to_csv(out_dir / f"{tag}_alerts.csv", index=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["noaa","amsa","all"], default="noaa")
    p.add_argument("--out", default="data/processed")
    p.add_argument("--bbox", choices=list(BBOXES.keys()), default=None)
    p.add_argument("--amsa-file", default=None)
    args = p.parse_args()
    out = Path(args.out)

    if args.source in ("noaa","all"):
        run_noaa(out, args.bbox)
    if args.source in ("amsa","all") and args.amsa_file:
        run_amsa(args.amsa_file, out, args.bbox)

if __name__ == "__main__":
    main()
