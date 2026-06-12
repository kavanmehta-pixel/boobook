"""AMSA/CTS AIS CSV normalisation.

The MVP accepts user-downloaded AMSA Spatial/Craft Tracking System CSVs or
similar AIS exports and maps common column variants to Boobook's canonical
schema:

mmsi,timestamp,lat,lon,sog,cog,vessel_name,vessel_type,source
"""
from __future__ import annotations
from pathlib import Path
import zipfile
import pandas as pd

CANONICAL_COLUMNS = ["mmsi", "timestamp", "lat", "lon", "sog", "cog", "vessel_name", "vessel_type", "source"]

ALIASES: dict[str, list[str]] = {
    "mmsi": ["mmsi", "MMSI", "MaritimeMobileServiceIdentity", "maritime_mobile_service_identity"],
    "timestamp": ["timestamp", "BaseDateTime", "datetime", "DateTime", "date_time", "time", "Time", "Position Time", "position_time", "ReportTime"],
    "lat": ["lat", "latitude", "LAT", "Latitude", "LATITUDE", "y", "Y"],
    "lon": ["lon", "long", "longitude", "LON", "Longitude", "LONGITUDE", "x", "X"],
    "sog": ["sog", "SOG", "speed", "Speed", "Speed Over Ground", "speed_over_ground"],
    "cog": ["cog", "COG", "course", "Course", "Course Over Ground", "course_over_ground"],
    "vessel_name": ["vessel_name", "VesselName", "Vessel Name", "name", "ShipName", "NAME", "ship_name"],
    "vessel_type": ["vessel_type", "VesselType", "Vessel Type", "type", "ShipType", "TYPE", "ship_type"],
}


def _pick_column(df: pd.DataFrame, names: list[str]) -> str | None:
    lower = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        if name in df.columns:
            return name
        key = name.strip().lower()
        if key in lower:
            return lower[key]
    return None


def _read_csv_or_zip(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"No CSV found inside zip: {path}")
            with zf.open(csv_names[0]) as fh:
                return pd.read_csv(fh, low_memory=False)
    return pd.read_csv(path, low_memory=False)


def normalise_dataframe(raw: pd.DataFrame, source: str = "user_csv") -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    out = pd.DataFrame(index=raw.index)
    for target, aliases in ALIASES.items():
        col = _pick_column(raw, aliases)
        if col is None:
            out[target] = "" if target in {"vessel_name", "vessel_type"} else pd.NA
        else:
            out[target] = raw[col]

    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    for col in ["lat", "lon", "sog", "cog"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["mmsi"] = out["mmsi"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    out["vessel_name"] = out["vessel_name"].fillna("").astype(str).str.strip()
    out["vessel_type"] = out["vessel_type"].fillna("").astype(str).str.strip()
    out["source"] = source

    out = out.dropna(subset=["mmsi", "timestamp", "lat", "lon"])
    out = out[out["mmsi"].ne("")]
    # Broad Australia + surrounding operating area sanity bounds.
    out = out[out["lat"].between(-48, -4) & out["lon"].between(95, 170)]
    out = out.sort_values(["mmsi", "timestamp"]).drop_duplicates(["mmsi", "timestamp", "lat", "lon"])
    return out[CANONICAL_COLUMNS].reset_index(drop=True)


def normalise_file(input_path: str | Path, output_path: str | Path | None = None) -> pd.DataFrame:
    raw = _read_csv_or_zip(input_path)
    df = normalise_dataframe(raw, source=Path(input_path).name)
    if output_path is not None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
    return df
