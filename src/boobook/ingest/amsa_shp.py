"""
AMSA CTS Shapefile ingestor.

Reads AMSA monthly vessel traffic shapefiles (cts_srr_MM_YYYY_pt.shp)
and normalises to the boobook canonical DataFrame format.

AMSA CTS shapefile columns:
  CRAFT_ID, LON, LAT, COURSE, SPEED, TYPE, SUBTYPE,
  LENGTH, BEAM, DRAUGHT, TIMESTAMP, geometry

Usage:
    from boobook.ingest.amsa_shp import load_amsa_shp
    df = load_amsa_shp("cts_srr_05_2026_pt.shp")
    df_ts = load_amsa_shp("cts_srr_05_2026_pt.shp", bbox=(141.0,-11.5,144.5,-8.5))
"""
from __future__ import annotations
import logging
from pathlib import Path
import pandas as pd

log = logging.getLogger(__name__)

# Map AMSA TYPE strings → boobook canonical vessel_type
_TYPE_MAP = {
    "Fishing":                     "Fishing",
    "Cargo ship - All":            "Cargo",
    "Cargo ship - No additional info": "Cargo",
    "Tanker - All":                "Tanker",
    "Tanker - No additional info": "Tanker",
    "Pilot vessel":                "Pilot",
    "Tug":                         "Tug",
    "Law enforcement":             "Law_enforcement",
    "Sailing":                     "Sailing",
    "Pleasure craft":              "Pleasure",
    "Passenger ship - All":        "Passenger",
    "Engaged in military operations": "Military",
    "SAR":                         "SAR",
    "Dredger":                     "Dredger",
    "unknown code 0":              "Unknown",
}

def _map_type(raw) -> str:
    if pd.isna(raw) or raw is None:
        return "Unknown"
    r = str(raw).strip()
    if r in _TYPE_MAP:
        return _TYPE_MAP[r]
    # Partial match
    for k, v in _TYPE_MAP.items():
        if k.lower() in r.lower():
            return v
    return "Other"



def _parse_amsa_timestamps(series: "pd.Series") -> "pd.Series":
    """Parse AMSA CTS timestamp strings to UTC.

    Handles two known formats:
      '16/05/2026 11:22:47 AM'  (2026 files)
      '2/12/2022 5:06:00 PM'    (2022 files)
    Both are day/month/year, 12-hour clock, Australian local time (AEST/AWST).
    CTS data is recorded in UTC per AMSA documentation.
    """
    # Try specific format first (fast), fall back to inference
    try:
        return pd.to_datetime(series, format="%d/%m/%Y %I:%M:%S %p", errors="coerce", utc=True)
    except Exception:
        pass
    # Mixed-format fallback
    parsed = pd.to_datetime(series, dayfirst=True, errors="coerce")
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize("UTC")
    return parsed


def load_amsa_shp(
    path: str | Path,
    bbox: tuple[float, float, float, float] | None = None,
    month_label: str | None = None,
) -> pd.DataFrame:
    """
    Load an AMSA CTS shapefile into canonical boobook DataFrame.

    Parameters
    ----------
    path:        Path to .shp file (or directory containing it).
    bbox:        (lon_min, lat_min, lon_max, lat_max) spatial clip.
                 Torres Strait: (141.0, -11.5, 144.5, -8.5)
    month_label: e.g. '2026-05' — used as source tag.

    Returns
    -------
    DataFrame with columns: mmsi, timestamp, lat, lon, sog, cog,
                            vessel_name, vessel_type, source
    """
    try:
        import geopandas as gpd
    except ImportError:
        raise ImportError("geopandas required: pip install geopandas fiona")

    path = Path(path)
    # If directory, find the .shp inside
    if path.is_dir():
        shps = list(path.glob("*.shp"))
        if not shps:
            raise FileNotFoundError(f"No .shp file in {path}")
        path = shps[0]

    log.info("Loading AMSA shp: %s  bbox=%s", path.name, bbox)

    # Spatial bbox filter at read time if possible
    if bbox is not None:
        from shapely.geometry import box
        lon_min, lat_min, lon_max, lat_max = bbox
        mask = box(lon_min, lat_min, lon_max, lat_max)
        gdf = gpd.read_file(path, mask=mask)
    else:
        gdf = gpd.read_file(path)

    log.info("Raw rows: %d", len(gdf))

    if gdf.empty:
        return pd.DataFrame(columns=["mmsi","timestamp","lat","lon","sog","cog","vessel_name","vessel_type","source"])

    label = month_label or path.stem
    source = f"AMSA_CTS_{label}"

    df = pd.DataFrame({
        "mmsi":        gdf["CRAFT_ID"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip(),
        "timestamp":   _parse_amsa_timestamps(gdf["TIMESTAMP"]),
        "lat":         pd.to_numeric(gdf["LAT"],   errors="coerce"),
        "lon":         pd.to_numeric(gdf["LON"],   errors="coerce"),
        "sog":         pd.to_numeric(gdf["SPEED"], errors="coerce"),
        "cog":         pd.to_numeric(gdf["COURSE"],errors="coerce"),
        "vessel_name": "",   # AMSA CTS pt layer has no vessel name field
        "vessel_type": gdf["TYPE"].apply(_map_type),
        "source":      source,
    })

    df = df.dropna(subset=["mmsi","timestamp","lat","lon"])
    df = df[df["mmsi"].ne("") & df["mmsi"].ne("nan")]
    # Filter invalid CRAFT_IDs: negative values are AMSA internal tracking IDs, not MMSIs
    df = df[~df["mmsi"].str.startswith("-")]
    df = df.sort_values(["mmsi","timestamp"]).drop_duplicates(["mmsi","timestamp","lat","lon"])
    log.info("AMSA load: %d rows, %d vessels", len(df), df["mmsi"].nunique())
    return df.reset_index(drop=True)
