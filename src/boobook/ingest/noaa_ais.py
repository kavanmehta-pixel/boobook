"""
NOAA MarineCadastre AIS ingestor.

Normalises NOAA daily AIS CSV → boobook canonical DataFrame format:
  mmsi, timestamp, lat, lon, sog, cog, vessel_name, vessel_type, source

NOAA columns: MMSI, BaseDateTime, LAT, LON, SOG, COG, Heading,
              VesselName, IMO, CallSign, VesselType, Status,
              Length, Width, Draft, Cargo, TransceiverClass

Usage:
    from boobook.ingest.noaa_ais import load_noaa_csv
    df = load_noaa_csv("AIS_2023_01_01.csv")
    df_torres = load_noaa_csv("AIS_2023_01_01.csv", bbox=(141.0, -11.5, 144.5, -8.5))
"""
from __future__ import annotations
import logging
from pathlib import Path
import pandas as pd

log = logging.getLogger(__name__)

# AIS VesselType numeric code → human label (ITU/AIS standard, bucketed by tens)
_TYPE_MAP = {
    0: "Unknown", 20: "WIG", 30: "Fishing", 31: "Towing", 32: "Towing_large",
    33: "Dredger", 34: "Diving", 35: "Military", 36: "Sailing", 37: "Pleasure",
    40: "HSC", 50: "Pilot", 51: "SAR", 52: "Tug", 53: "Port_tender",
    55: "Law_enforcement", 60: "Passenger", 70: "Cargo", 80: "Tanker", 90: "Other",
}

def _vessel_type_label(code) -> str:
    if pd.isna(code):
        return "Unknown"
    c = int(code)
    return _TYPE_MAP.get(c, _TYPE_MAP.get((c // 10) * 10, "Unknown"))


def load_noaa_csv(
    path: str | Path,
    chunksize: int = 200_000,
    bbox: tuple[float, float, float, float] | None = None,
) -> pd.DataFrame:
    """
    Load NOAA AIS CSV into a canonical boobook DataFrame.

    Parameters
    ----------
    path:      Path to AIS_YYYY_MM_DD.csv
    chunksize: Rows per chunk (keeps RAM flat on 800MB+ files)
    bbox:      (lon_min, lat_min, lon_max, lat_max) spatial clip, optional.
               Torres Strait: (141.0, -11.5, 144.5, -8.5)

    Returns
    -------
    DataFrame with columns: mmsi, timestamp, lat, lon, sog, cog,
                            vessel_name, vessel_type, source
    """
    path = Path(path)
    log.info("Loading NOAA AIS: %s  bbox=%s", path.name, bbox)

    chunks = []
    total = kept = 0

    for chunk in pd.read_csv(
        path,
        dtype={"MMSI": str, "VesselName": str, "IMO": str,
               "CallSign": str, "TransceiverClass": str},
        parse_dates=["BaseDateTime"],
        chunksize=chunksize,
    ):
        total += len(chunk)
        chunk = chunk.dropna(subset=["LAT", "LON", "BaseDateTime"])

        if bbox is not None:
            lon_min, lat_min, lon_max, lat_max = bbox
            chunk = chunk[
                chunk["LON"].between(lon_min, lon_max) &
                chunk["LAT"].between(lat_min, lat_max)
            ]

        if chunk.empty:
            continue

        out = pd.DataFrame({
            "mmsi":        chunk["MMSI"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip(),
            "timestamp":   pd.to_datetime(chunk["BaseDateTime"], utc=True),
            "lat":         chunk["LAT"].astype(float),
            "lon":         chunk["LON"].astype(float),
            "sog":         pd.to_numeric(chunk["SOG"], errors="coerce"),
            "cog":         pd.to_numeric(chunk["COG"], errors="coerce"),
            "vessel_name": chunk["VesselName"].fillna("").astype(str).str.strip(),
            "vessel_type": chunk["VesselType"].apply(_vessel_type_label),
            "source":      "NOAA_MarineCadastre",
        })
        chunks.append(out)
        kept += len(out)

    log.info("NOAA load: %d rows → %d kept (%.1f%%)", total, kept, 100*kept/max(total,1))

    if not chunks:
        return pd.DataFrame(columns=["mmsi","timestamp","lat","lon","sog","cog","vessel_name","vessel_type","source"])

    df = pd.concat(chunks, ignore_index=True)
    df = df.sort_values(["mmsi", "timestamp"]).drop_duplicates(["mmsi", "timestamp", "lat", "lon"])
    return df.reset_index(drop=True)
