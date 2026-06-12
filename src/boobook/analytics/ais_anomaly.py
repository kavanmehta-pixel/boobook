"""AIS anomaly detection — Boobook source-data validation layer.

Five detection rules:
  1. AIS gap          — transmission silence exceeding threshold
  2. Impossible speed — implied speed physically implausible (spoofing indicator)
  3. Loitering        — sustained low-speed presence in small radius
  4. Rendezvous       — two different vessels in close proximity simultaneously
  5. Sensitive zone   — vessel present inside a configured monitoring zone

All scores, thresholds and parameters are soft-configurable.
Outputs are hedged: anomalies flag for human review, not proof of illegality.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import pandas as pd
from boobook.utils_geo import haversine_km, implied_speed_knots
from boobook.config import SENSITIVE_ZONES

# Vessel types that elevate risk scores in remote-area anomaly contexts
_HIGH_CONCERN_TYPES = {"Fishing", "Tanker", "Unknown", "Other", ""}


@dataclass
class Alert:
    alert_id: str
    alert_type: str
    severity: str
    risk_score: int
    mmsi: str
    timestamp: str
    lat: float
    lon: float
    vessel_name: str
    vessel_type: str
    title: str
    explanation: str
    recommended_action: str
    evidence: str


def _severity(score: int) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 55:
        return "MEDIUM"
    return "LOW"


def _alert(
    alerts: list[Alert],
    alert_type: str,
    score: int,
    mmsi: str,
    ts,
    lat: float,
    lon: float,
    vessel_name: str,
    vessel_type: str,
    title: str,
    explanation: str,
    action: str,
    evidence: str,
) -> None:
    alerts.append(
        Alert(
            alert_id=f"BKB-{len(alerts)+1:04d}",
            alert_type=alert_type,
            severity=_severity(score),
            risk_score=int(score),
            mmsi=str(mmsi),
            timestamp=pd.Timestamp(ts).isoformat(),
            lat=float(lat),
            lon=float(lon),
            vessel_name=str(vessel_name),
            vessel_type=str(vessel_type),
            title=title,
            explanation=explanation,
            recommended_action=action,
            evidence=evidence,
        )
    )


# ---------------------------------------------------------------------------
# Rule 1: AIS gap
# ---------------------------------------------------------------------------
def detect_gaps(df: pd.DataFrame, threshold_hours: float = 2.0) -> list[Alert]:
    """Flag vessels where AIS transmission silence exceeds threshold."""
    alerts: list[Alert] = []
    for mmsi, g in df.sort_values(["mmsi", "timestamp"]).groupby("mmsi", sort=False):
        g = g.reset_index(drop=True)
        vtype = str(g.loc[0, "vessel_type"]) if "vessel_type" in g.columns else ""
        vname = str(g.loc[0, "vessel_name"]) if "vessel_name" in g.columns else ""
        is_concern = vtype in _HIGH_CONCERN_TYPES
        for i in range(1, len(g)):
            dt_h = (
                g.loc[i, "timestamp"] - g.loc[i - 1, "timestamp"]
            ).total_seconds() / 3600
            if dt_h >= threshold_hours:
                base = 55 if not is_concern else 62
                score = min(95, base + int((dt_h - threshold_hours) * 8))
                _alert(
                    alerts,
                    "AIS_GAP",
                    score,
                    mmsi,
                    g.loc[i, "timestamp"],
                    g.loc[i, "lat"],
                    g.loc[i, "lon"],
                    vname,
                    vtype,
                    f"AIS gap of {dt_h:.1f} h",
                    "The vessel disappeared from the AIS source feed for longer than the "
                    "configured threshold. This may indicate intentional disabling, poor "
                    "coverage, equipment failure, or small-vessel below-threshold operation.",
                    "Review track before/after gap; cross-check RF, SAR, patrol and VMS "
                    "sources. Note whether the gap area coincides with known IUU activity.",
                    f"Previous point {g.loc[i-1, 'timestamp'].isoformat()} → "
                    f"current point {g.loc[i, 'timestamp'].isoformat()} "
                    f"({dt_h:.1f} h silence).",
                )
    return alerts


# ---------------------------------------------------------------------------
# Rule 2: Impossible implied speed
# ---------------------------------------------------------------------------
def detect_impossible_speed(
    df: pd.DataFrame, max_implied_knots: float = 45.0
) -> list[Alert]:
    """Detect AIS spoofing / track-stitching errors via implausible implied speeds."""
    alerts: list[Alert] = []
    for mmsi, g in df.sort_values(["mmsi", "timestamp"]).groupby("mmsi", sort=False):
        g = g.reset_index(drop=True)
        vtype = str(g.loc[0, "vessel_type"]) if "vessel_type" in g.columns else ""
        vname = str(g.loc[0, "vessel_name"]) if "vessel_name" in g.columns else ""
        for i in range(1, len(g)):
            speed_kn = implied_speed_knots(
                g.loc[i - 1, "lat"], g.loc[i - 1, "lon"], g.loc[i - 1, "timestamp"],
                g.loc[i, "lat"], g.loc[i, "lon"], g.loc[i, "timestamp"],
            )
            if speed_kn >= max_implied_knots:
                speed_delta = speed_kn - max_implied_knots
                import math
                if math.isinf(speed_delta) or math.isnan(speed_delta) or speed_delta > 1e9:
                    score = 98
                else:
                    score = min(98, 70 + int(speed_delta / 5))
                _alert(
                    alerts,
                    "IMPOSSIBLE_SPEED",
                    score,
                    mmsi,
                    g.loc[i, "timestamp"],
                    g.loc[i, "lat"],
                    g.loc[i, "lon"],
                    vname,
                    vtype,
                    f"Implied speed {speed_kn:.0f} kn — possible spoofing",
                    "Successive AIS positions imply a physically impossible speed, strongly "
                    "suggesting AIS position spoofing, a false-identity broadcast, or a "
                    "track-stitching error merging two different vessels.",
                    "Inspect raw source rows. Compare against alternative AIS feeds, "
                    "RF/SAR/patrol data. Do not assume identity continuity across this jump.",
                    f"Implied speed {speed_kn:.1f} kn between "
                    f"{g.loc[i-1, 'timestamp'].isoformat()} and "
                    f"{g.loc[i, 'timestamp'].isoformat()}.",
                )
    return alerts


# ---------------------------------------------------------------------------
# Rule 3: Loitering
# ---------------------------------------------------------------------------
def detect_loitering(
    df: pd.DataFrame,
    min_hours: float = 2.0,
    radius_km: float = 5.0,
    max_avg_sog: float = 3.0,
) -> list[Alert]:
    """Detect sustained low-speed presence inside a small area."""
    alerts: list[Alert] = []
    for mmsi, g in df.sort_values(["mmsi", "timestamp"]).groupby("mmsi", sort=False):
        if len(g) < 3:
            continue
        vtype = str(g.iloc[0].get("vessel_type", ""))
        vname = str(g.iloc[0].get("vessel_name", ""))
        is_concern = vtype in _HIGH_CONCERN_TYPES
        span_h = (g["timestamp"].max() - g["timestamp"].min()).total_seconds() / 3600
        centre_lat, centre_lon = float(g["lat"].mean()), float(g["lon"].mean())
        max_radius = max(
            haversine_km(centre_lat, centre_lon, row.lat, row.lon)
            for row in g.itertuples()
        )
        avg_sog = float(pd.to_numeric(g["sog"], errors="coerce").fillna(0).mean())
        if span_h >= min_hours and max_radius <= radius_km and avg_sog <= max_avg_sog:
            base = 60 if not is_concern else 70
            score = min(88, base + int(span_h * 3))
            row = g.sort_values("timestamp").iloc[-1]
            _alert(
                alerts,
                "LOITERING",
                score,
                mmsi,
                row["timestamp"],
                row["lat"],
                row["lon"],
                vname,
                vtype,
                f"Loitering {span_h:.1f} h within {max_radius:.1f} km",
                "The vessel remains inside a small geographic radius at low average speed "
                "for a sustained period. In northern Australian waters, this pattern is "
                "consistent with IUU fishing activity or sea-cucumber harvesting.",
                "Check whether the area is consistent with a licensed fishing zone, "
                "anchorage, or known permitted activity. Cross-reference against AFMA "
                "authorisation records and VMS data if available.",
                f"Span {span_h:.1f} h; max radius from centroid {max_radius:.2f} km; "
                f"avg SOG {avg_sog:.1f} kn.",
            )
    return alerts


# ---------------------------------------------------------------------------
# Rule 4: Rendezvous
# ---------------------------------------------------------------------------
def detect_rendezvous(
    df: pd.DataFrame,
    window_minutes: float = 30,
    distance_km: float = 2.0,
    exclude_same_type_patrol: bool = True,
) -> list[Alert]:
    """Detect two different vessels appearing very close in space and time.

    Vectorised: rounds timestamps to window buckets, then uses spatial
    binning to avoid O(n^2) comparison across all row pairs.
    """
    import math
    alerts: list[Alert] = []
    if len(df) < 2:
        return alerts

    rows = df.sort_values("timestamp").reset_index(drop=True).copy()
    patrol_types = {"Law_enforcement", "Military", "SAR"}

    # Build vessel metadata
    vtype_map = rows.groupby("mmsi")["vessel_type"].first().to_dict() if "vessel_type" in rows.columns else {}
    vname_map = rows.groupby("mmsi")["vessel_name"].first().to_dict() if "vessel_name" in rows.columns else {}

    # Round timestamps to window bucket
    bucket_s = int(window_minutes * 60)
    rows["_bucket"] = (rows["timestamp"].astype("int64") // 1_000_000_000 // bucket_s).astype(int)

    # Spatial bin: ~2km grid cell at equator
    deg_per_km = 1 / 111.0
    cell_size = distance_km * deg_per_km
    rows["_lat_bin"] = (rows["lat"] / cell_size).astype(int)
    rows["_lon_bin"] = (rows["lon"] / cell_size).astype(int)

    seen_pairs: set[tuple] = set()

    for (bucket, lat_bin, lon_bin), grp in rows.groupby(["_bucket", "_lat_bin", "_lon_bin"]):
        vessels = grp["mmsi"].unique()
        if len(vessels) < 2:
            continue
        # Check all vessel pairs in this cell+bucket
        for vi in range(len(vessels)):
            for vj in range(vi + 1, len(vessels)):
                a_mmsi, b_mmsi = str(vessels[vi]), str(vessels[vj])
                pair = (min(a_mmsi, b_mmsi), max(a_mmsi, b_mmsi))
                if pair in seen_pairs:
                    continue
                a_type = str(vtype_map.get(a_mmsi, ""))
                b_type = str(vtype_map.get(b_mmsi, ""))
                if exclude_same_type_patrol and a_type in patrol_types and b_type in patrol_types:
                    continue
                # Get representative rows for distance
                a_rows = grp[grp["mmsi"].astype(str) == a_mmsi]
                b_rows = grp[grp["mmsi"].astype(str) == b_mmsi]
                if a_rows.empty or b_rows.empty:
                    continue
                a_row = a_rows.iloc[0]
                b_row = b_rows.iloc[0]
                dist = haversine_km(a_row["lat"], a_row["lon"], b_row["lat"], b_row["lon"])
                if dist > distance_km:
                    continue
                seen_pairs.add(pair)
                dt_min = abs((b_row["timestamp"] - a_row["timestamp"]).total_seconds()) / 60
                score = 78
                a_name = vname_map.get(a_mmsi, a_mmsi)
                b_name = vname_map.get(b_mmsi, b_mmsi)
                _alert(
                    alerts, "RENDEZVOUS_CANDIDATE", score,
                    a_mmsi, a_row["timestamp"], a_row["lat"], a_row["lon"],
                    a_name, a_type,
                    f"Possible rendezvous with {b_name}",
                    f"Two vessels appeared within {dist:.2f}km of each other within the time window. "
                    f"Vessel-to-vessel transfers (catch, fuel, crew) are a known IUU evasion method.",
                    "Check vessel types, flag states, licensed activity, and AIS gap history for both parties.",
                    f"{a_mmsi}/{b_mmsi}; separation {dist:.2f}km; time delta {dt_min:.0f}min.",
                )
    return alerts


def detect_sensitive_zone(
    df: pd.DataFrame, zones: list[dict] | None = None
) -> list[Alert]:
    """Flag vessel presence inside configured monitoring zones."""
    zones = zones or SENSITIVE_ZONES
    alerts: list[Alert] = []
    for row in df.itertuples(index=False):
        for z in zones:
            d = haversine_km(row.lat, row.lon, z["lat"], z["lon"])
            if d <= z["radius_km"]:
                vtype = str(getattr(row, "vessel_type", ""))
                vname = str(getattr(row, "vessel_name", ""))
                _alert(
                    alerts,
                    "SENSITIVE_ZONE",
                    52,
                    row.mmsi,
                    row.timestamp,
                    row.lat,
                    row.lon,
                    vname,
                    vtype,
                    f"Presence inside {z['name']}",
                    "The vessel is inside an illustrative monitoring zone. This is "
                    "contextual enrichment, not an allegation of wrongdoing.",
                    "Use as a contextual feature alongside gap/loitering/rendezvous "
                    "alerts rather than as a standalone escalation trigger.",
                    f"Distance to zone centre {d:.1f} km; zone radius {z['radius_km']:.1f} km.",
                )
                break
    return alerts


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def run_validation(
    df: pd.DataFrame, *, gap_hours: float = 2.0
) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    """Run all detection rules and produce structured outputs."""
    if df.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            {"type": "FeatureCollection", "features": []},
            {"rows": 0, "vessels": 0, "alerts": 0},
        )
    work = df.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], utc=True)

    alerts: list[Alert] = []
    alerts.extend(detect_gaps(work, threshold_hours=gap_hours))
    alerts.extend(detect_impossible_speed(work))
    alerts.extend(detect_loitering(work))
    alerts.extend(detect_rendezvous(work))
    # Sensitive zone: last known point per vessel only (keep volume manageable)
    latest = work.sort_values("timestamp").groupby("mmsi", as_index=False).tail(1)
    alerts.extend(detect_sensitive_zone(latest))

    alerts_df = pd.DataFrame([asdict(a) for a in alerts])
    if not alerts_df.empty:
        alerts_df = alerts_df.sort_values(
            ["risk_score", "timestamp"], ascending=[False, True]
        ).reset_index(drop=True)

    risk_by_mmsi: dict[str, int] = {}
    for a in alerts:
        for m in str(a.mmsi).split("|"):
            risk_by_mmsi[m] = max(risk_by_mmsi.get(m, 0), a.risk_score)

    vessel_rows = []
    for mmsi, g in work.groupby("mmsi"):
        last = g.sort_values("timestamp").iloc[-1]
        vessel_rows.append(
            {
                "mmsi": str(mmsi),
                "vessel_name": str(last.get("vessel_name", "")),
                "vessel_type": str(last.get("vessel_type", "")),
                "positions": int(len(g)),
                "first_seen": g["timestamp"].min().isoformat(),
                "last_seen": g["timestamp"].max().isoformat(),
                "last_lat": float(last["lat"]),
                "last_lon": float(last["lon"]),
                "risk_score": int(risk_by_mmsi.get(str(mmsi), 0)),
            }
        )
    vessels_df = pd.DataFrame(vessel_rows).sort_values(
        "risk_score", ascending=False
    ).reset_index(drop=True)

    features = []
    for mmsi, g in work.sort_values("timestamp").groupby("mmsi"):
        coords = [[float(r.lon), float(r.lat)] for r in g.itertuples(index=False)]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "mmsi": str(mmsi),
                    "vessel_name": str(g.iloc[-1].get("vessel_name", "")),
                    "vessel_type": str(g.iloc[-1].get("vessel_type", "")),
                    "risk_score": int(risk_by_mmsi.get(str(mmsi), 0)),
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            }
        )
    tracks_geojson = {"type": "FeatureCollection", "features": features}

    summary = {
        "rows": int(len(work)),
        "vessels": int(work["mmsi"].nunique()),
        "alerts": int(len(alerts_df)),
        "high_alerts": int((alerts_df["severity"] == "HIGH").sum())
        if not alerts_df.empty
        else 0,
        "medium_alerts": int((alerts_df["severity"] == "MEDIUM").sum())
        if not alerts_df.empty
        else 0,
        "time_min": work["timestamp"].min().isoformat(),
        "time_max": work["timestamp"].max().isoformat(),
        "alert_types": alerts_df["alert_type"].value_counts().to_dict()
        if not alerts_df.empty
        else {},
    }
    return alerts_df, vessels_df, tracks_geojson, summary


def write_validation_outputs(
    df: pd.DataFrame, out_dir: str | Path, gap_hours: float = 2.0
) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    alerts_df, vessels_df, tracks_geojson, summary = run_validation(
        df, gap_hours=gap_hours
    )
    paths = {
        "normalised": str(out / "normalised_ais.csv"),
        "alerts": str(out / "alerts.csv"),
        "vessels": str(out / "vessels.csv"),
        "tracks": str(out / "tracks.geojson"),
        "summary": str(out / "summary.json"),
    }
    df.to_csv(paths["normalised"], index=False)
    alerts_df.to_csv(paths["alerts"], index=False)
    vessels_df.to_csv(paths["vessels"], index=False)
    Path(paths["tracks"]).write_text(
        json.dumps(tracks_geojson, indent=2), encoding="utf-8"
    )
    Path(paths["summary"]).write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return paths
