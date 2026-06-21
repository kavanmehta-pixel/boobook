#!/usr/bin/env python3
"""
Generate a realistic synthetic AIS dataset for Torres Strait.

Based on:
- AFMA annual report intercept patterns
- Global Fishing Watch Torres Strait fishing effort data
- Known IUU vessel behaviour from arXiv:2502.01503

Produces ~5,000 AIS records across 30 days (Jan 2023) for:
  - 8 Indonesian fishing vessels (IUU risk)
  - 4 PNG fishing vessels (mixed compliance)
  - 3 Australian licensed vessels
  - 2 ABF patrol vessels
  - 2 cargo vessels (transit)
  - 1 dark vessel (AIS gaps + RF-only detection scenario)

All coordinates within Torres Strait bounding box: 
  lon 141.0–144.5, lat -11.5–-8.5
"""
from __future__ import annotations
import sys, random, math
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

random.seed(42)
np.random.seed(42)

# Torres Strait area bounds
LAT_MIN, LAT_MAX = -11.5, -8.5
LON_MIN, LON_MAX = 141.0, 144.5

# Key areas
TORRES_STRAIT_CENTER = (-10.58, 142.22)
GULF_ENTRY           = (-10.2,  141.5)
ARAFURA_ENTRY        = (-10.8,  143.5)
PNG_COAST            = (-9.2,   142.8)
THURSDAY_ISLAND      = (-10.58, 142.22)
CORAL_SEA_ENTRY      = (-10.1,  143.8)

START = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def move(lat, lon, heading_deg, speed_kn, hours):
    """Move a vessel from (lat,lon) by speed/heading for given hours."""
    dist_km = speed_kn * 1.852 * hours
    heading_rad = math.radians(heading_deg)
    dlat = (dist_km / 111.0) * math.cos(heading_rad)
    dlon = (dist_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(heading_rad)
    new_lat = lat + dlat
    new_lon = lon + dlon
    # Clamp to bbox
    new_lat = max(LAT_MIN + 0.1, min(LAT_MAX - 0.1, new_lat))
    new_lon = max(LON_MIN + 0.1, min(LON_MAX - 0.1, new_lon))
    return new_lat, new_lon

def make_track(
    mmsi, name, vtype, flag,
    start_lat, start_lon,
    days, ping_interval_min=30,
    pattern="transit",
    ais_gaps=None,   # list of (start_hour, duration_hours) — AIS silence periods
    speed_mean=5.0, speed_std=1.5,
):
    """Generate a vessel track as a list of row dicts."""
    rows = []
    lat, lon = start_lat, start_lon
    heading = random.uniform(0, 360)
    t = START + timedelta(days=random.uniform(0, 5))  # stagger start times

    end_t = START + timedelta(days=days)
    ais_gaps = ais_gaps or []
    # Convert gap specs to absolute datetimes
    abs_gaps = [
        (START + timedelta(hours=h), timedelta(hours=dur))
        for h, dur in ais_gaps
    ]

    while t < end_t:
        # Check if inside a gap
        in_gap = any(gs <= t < gs + gd for gs, gd in abs_gaps)

        if not in_gap:
            sog = max(0.1, random.gauss(speed_mean, speed_std))
            cog = (heading + random.gauss(0, 15)) % 360
            rows.append({
                "mmsi":        mmsi,
                "timestamp":   t.isoformat(),
                "lat":         round(lat + random.gauss(0, 0.001), 5),
                "lon":         round(lon + random.gauss(0, 0.001), 5),
                "sog":         round(sog, 1),
                "cog":         round(cog, 1),
                "vessel_name": name,
                "vessel_type": vtype,
                "source":      f"SYNTHETIC_TORRES_{flag}",
            })

        # Move vessel
        interval_h = ping_interval_min / 60.0
        lat, lon = move(lat, lon, heading, speed_mean, interval_h)

        # Pattern-based heading changes
        if pattern == "fishing":
            # Fishing: slow, circular, occasional direction reversal
            if random.random() < 0.15:
                heading = random.uniform(0, 360)
        elif pattern == "loitering":
            # Loitering: stay in small area
            heading = (heading + random.gauss(0, 45)) % 360
            if haversine_km(lat, lon, start_lat, start_lon) > 4.0:
                # Drift back toward start
                dlat = start_lat - lat
                dlon = start_lon - lon
                heading = (math.degrees(math.atan2(dlon, dlat))) % 360
        elif pattern == "transit":
            # Transit: mostly straight with minor deviations
            heading = (heading + random.gauss(0, 5)) % 360
        elif pattern == "patrol":
            # Patrol: systematic coverage
            if random.random() < 0.05:
                heading = random.choice([45, 135, 225, 315])

        t += timedelta(minutes=ping_interval_min)

    return rows

# ── Build fleet ──────────────────────────────────────────────────────────────
all_rows = []

# 1. Indonesian fishing vessels — IUU risk, fishing patterns, some gaps
idn_vessels = [
    ("5100100"+str(i), f"IDN FISHER {i:02d}", "Fishing", "IDN")
    for i in range(1, 9)
]
for i, (mmsi, name, vtype, flag) in enumerate(idn_vessels):
    # Scatter starting positions across the strait
    lat = random.uniform(-11.3, -9.5)
    lon = random.uniform(141.2, 143.8)
    # Some have AIS gaps
    gaps = []
    if i < 4:  # 4 of 8 have gaps
        gap_start = random.randint(24, 480)
        gap_dur   = random.uniform(4, 18)
        gaps = [(gap_start, gap_dur)]
        if i < 2:  # 2 have multiple gaps
            gaps.append((gap_start + random.randint(48, 120), random.uniform(6, 12)))
    all_rows.extend(make_track(
        mmsi, name, vtype, flag,
        lat, lon, days=28,
        ping_interval_min=random.choice([20, 30, 45]),
        pattern="fishing" if i % 3 != 0 else "loitering",
        ais_gaps=gaps,
        speed_mean=random.uniform(1.5, 4.0),
        speed_std=0.8,
    ))

# 2. PNG fishing vessels — mixed compliance
png_vessels = [
    (f"553000{100+i}", f"PNG VESSEL {i:02d}", "Fishing", "PNG")
    for i in range(1, 5)
]
for i, (mmsi, name, vtype, flag) in enumerate(png_vessels):
    lat = random.uniform(-10.5, -9.0)
    lon = random.uniform(142.0, 144.0)
    all_rows.extend(make_track(
        mmsi, name, vtype, flag,
        lat, lon, days=20,
        ping_interval_min=30,
        pattern="fishing",
        speed_mean=2.5, speed_std=1.0,
    ))

# 3. Australian licensed fishing vessels
aus_vessels = [
    (f"50300{700+i}", f"AUS LICENSED {i:02d}", "Fishing", "AUS")
    for i in range(1, 4)
]
for i, (mmsi, name, vtype, flag) in enumerate(aus_vessels):
    lat = random.uniform(-11.0, -10.0)
    lon = random.uniform(141.5, 143.0)
    all_rows.extend(make_track(
        mmsi, name, vtype, flag,
        lat, lon, days=25,
        ping_interval_min=15,  # Compliant vessels ping more frequently
        pattern="fishing",
        speed_mean=3.0, speed_std=0.5,
    ))

# 4. ABF patrol vessels — systematic coverage
patrol_vessels = [
    ("503700001", "ABFV CAPE FOURCROY", "Law_enforcement", "AUS"),
    ("503700002", "ABFV CAPE YORK",     "Law_enforcement", "AUS"),
]
for i, (mmsi, name, vtype, flag) in enumerate(patrol_vessels):
    lat = THURSDAY_ISLAND[0] + i * 0.3
    lon = THURSDAY_ISLAND[1] + i * 0.2
    all_rows.extend(make_track(
        mmsi, name, vtype, flag,
        lat, lon, days=30,
        ping_interval_min=10,  # Patrol vessels ping very frequently
        pattern="patrol",
        speed_mean=12.0, speed_std=2.0,
    ))

# 5. Cargo vessels — transiting the strait
cargo_vessels = [
    ("477123456", "PACIFIC TRADER",    "Cargo", "HKG"),
    ("9V123456",  "SINGAPORE EXPRESS", "Cargo", "SGP"),
]
for i, (mmsi, name, vtype, flag) in enumerate(cargo_vessels):
    lat = -11.2
    lon = 141.1 + i * 0.2
    all_rows.extend(make_track(
        mmsi, name, vtype, flag,
        lat, lon, days=2,   # Just transiting, 2 days in the strait
        ping_interval_min=10,
        pattern="transit",
        speed_mean=14.0, speed_std=1.0,
    ))

# 6. DARK VESSEL — AIS mostly off, only occasional pings
# This is the star of the show: the vessel ninox is designed to detect
all_rows.extend(make_track(
    "510099999", "DARK VESSEL", "Fishing", "IDN",
    start_lat=-10.9, start_lon=143.2,
    days=28,
    ping_interval_min=180,  # Pings only every 3 hours
    pattern="loitering",
    ais_gaps=[
        (12,  48),   # 48h silence in first week
        (120, 72),   # 72h silence — major dark event
        (240, 36),   # 36h silence
        (360, 24),   # 24h silence
    ],
    speed_mean=1.2, speed_std=0.3,
))

# ── Build DataFrame ──────────────────────────────────────────────────────────
df = pd.DataFrame(all_rows)
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df = df.sort_values(["mmsi","timestamp"]).reset_index(drop=True)

# Add some realistic noise — a few impossible speed jumps (spoofing simulation)
spoof_mmsi = "5100100" + str(random.randint(1,4))
spoof_idx = df[df["mmsi"]==spoof_mmsi].index[5]
df.loc[spoof_idx, "lat"] += random.uniform(2.0, 4.0)   # Jump ~300km
df.loc[spoof_idx, "lon"] += random.uniform(2.0, 4.0)

# Rendezvous event — two IDN vessels get close at the same time
rv_mmsi_a = "51001001"
rv_mmsi_b = "51001002"
rv_time = START + timedelta(days=10, hours=6)
rv_idx_a = df[(df["mmsi"]==rv_mmsi_a)].index
rv_idx_b = df[(df["mmsi"]==rv_mmsi_b)].index
if len(rv_idx_a) > 0 and len(rv_idx_b) > 0:
    base_lat, base_lon = -10.6, 142.8
    df.loc[rv_idx_a[len(rv_idx_a)//3], ["lat","lon","timestamp"]] = [base_lat, base_lon, rv_time.isoformat()]
    df.loc[rv_idx_b[len(rv_idx_b)//3], ["lat","lon","timestamp"]] = [base_lat+0.008, base_lon+0.005, rv_time.isoformat()]

out_path = Path("data/sample/torres_strait_synthetic.csv")
out_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_path, index=False)

print(f"Generated Torres Strait synthetic dataset:")
print(f"  Rows:    {len(df):,}")
print(f"  Vessels: {df['mmsi'].nunique()}")
print(f"  Period:  {df['timestamp'].min()} → {df['timestamp'].max()}")
print(f"  Types:   {df['vessel_type'].value_counts().to_dict()}")
print(f"  Saved:   {out_path}")
