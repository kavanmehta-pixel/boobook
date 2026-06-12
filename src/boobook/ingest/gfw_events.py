"""
Global Fishing Watch events ingestor.

Handles GFW CSV event formats:
  - AIS-off events   (vessel disappeared from AIS)
  - Encounter events (two vessels meet at sea)
  - Fishing events   (inferred fishing activity)

GFW CSV schema varies by event type but always includes:
  vessel_id, vessel_mmsi, start, end, lat, lon, event_type, ...

These become pre-labelled training examples for boobook's anomaly engine.

Usage:
    from boobook.ingest.gfw_events import load_gfw_events
    df = load_gfw_events("gfw_ais_off_events.csv", event_type="ais_off")
"""
from __future__ import annotations
import logging
from pathlib import Path
import pandas as pd

log = logging.getLogger(__name__)

# Canonical output schema
GFW_COLUMNS = [
    "mmsi", "event_type", "start", "end", "lat", "lon",
    "duration_hours", "flag", "vessel_type", "source"
]

_MMSI_ALIASES   = ["vessel_mmsi", "mmsi", "MMSI", "ssvid"]
_START_ALIASES  = ["start", "event_start", "timestamp", "date_start", "start_time"]
_END_ALIASES    = ["end",   "event_end",   "date_end",  "end_time"]
_LAT_ALIASES    = ["lat", "latitude", "mean_latitude",  "event_lat"]
_LON_ALIASES    = ["lon", "longitude","mean_longitude", "event_lon"]
_FLAG_ALIASES   = ["vessel_flag", "flag", "iso3", "country_code"]
_VTYPE_ALIASES  = ["vessel_type", "ship_type", "geartype"]


def _pick(df: pd.DataFrame, aliases: list[str]):
    for a in aliases:
        if a in df.columns:
            return a
    return None


def load_gfw_events(
    path: str | Path,
    event_type: str = "unknown",
    bbox: tuple[float, float, float, float] | None = None,
) -> pd.DataFrame:
    """
    Load a GFW event CSV into a canonical DataFrame.

    Parameters
    ----------
    path:       Path to GFW CSV file.
    event_type: Human label — 'ais_off', 'encounter', 'fishing', etc.
    bbox:       (lon_min, lat_min, lon_max, lat_max) optional clip.

    Returns
    -------
    DataFrame with GFW_COLUMNS.
    """
    path = Path(path)
    log.info("Loading GFW events: %s  type=%s", path.name, event_type)

    df = pd.read_csv(path, low_memory=False)
    log.info("Raw rows: %d  columns: %s", len(df), list(df.columns))

    out = pd.DataFrame()
    out["mmsi"] = df.get(_pick(df, _MMSI_ALIASES) or "", pd.NA)
    out["event_type"] = event_type
    out["start"] = pd.to_datetime(df.get(_pick(df, _START_ALIASES) or "", pd.NA), errors="coerce", utc=True)
    out["end"]   = pd.to_datetime(df.get(_pick(df, _END_ALIASES)   or "", pd.NA), errors="coerce", utc=True)
    out["lat"]   = pd.to_numeric(df.get(_pick(df, _LAT_ALIASES)    or "", pd.NA), errors="coerce")
    out["lon"]   = pd.to_numeric(df.get(_pick(df, _LON_ALIASES)    or "", pd.NA), errors="coerce")
    out["flag"]  = df.get(_pick(df, _FLAG_ALIASES)  or "", "")
    out["vessel_type"] = df.get(_pick(df, _VTYPE_ALIASES) or "", "")
    out["source"] = f"GFW_{event_type}"

    # Duration
    valid_times = out["start"].notna() & out["end"].notna()
    out["duration_hours"] = pd.NA
    out.loc[valid_times, "duration_hours"] = (
        (out.loc[valid_times, "end"] - out.loc[valid_times, "start"])
        .dt.total_seconds() / 3600
    ).round(2)

    # Spatial clip
    if bbox is not None:
        lon_min, lat_min, lon_max, lat_max = bbox
        out = out[
            out["lon"].between(lon_min, lon_max) &
            out["lat"].between(lat_min, lat_max)
        ]

    out = out.dropna(subset=["mmsi", "start", "lat", "lon"])
    out["mmsi"] = out["mmsi"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

    log.info("GFW events loaded: %d rows", len(out))
    return out[GFW_COLUMNS].reset_index(drop=True)
