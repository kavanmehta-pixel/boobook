"""Tests for NOAA MarineCadastre AIS ingestor."""
import io
import pandas as pd
import pytest
from boobook.ingest.noaa_ais import load_noaa_csv, _vessel_type_label


# ── vessel type mapping ──────────────────────────────────────────────────────
class TestVesselTypeLabel:
    def test_exact_match(self):
        assert _vessel_type_label(30) == "Fishing"
        assert _vessel_type_label(70) == "Cargo"
        assert _vessel_type_label(80) == "Tanker"
        assert _vessel_type_label(55) == "Law_enforcement"

    def test_bucket_fallback(self):
        assert _vessel_type_label(71) == "Cargo"   # 71 → bucket 70
        assert _vessel_type_label(79) == "Cargo"   # 79 → bucket 70
        assert _vessel_type_label(31) == "Towing"  # exact match

    def test_zero_is_unknown(self):
        assert _vessel_type_label(0) == "Unknown"

    def test_nan_is_unknown(self):
        assert _vessel_type_label(float("nan")) == "Unknown"

    def test_unrecognised_code(self):
        # Code with no bucket match → Unknown
        assert _vessel_type_label(99) == "Other"   # bucket 90 = Other


# ── CSV loading ──────────────────────────────────────────────────────────────
NOAA_HEADER = "MMSI,BaseDateTime,LAT,LON,SOG,COG,Heading,VesselName,IMO,CallSign,VesselType,Status,Length,Width,Draft,Cargo,TransceiverClass\n"
NOAA_ROWS = [
    "368000001,2023-01-01T00:00:00,34.0,-118.0,5.0,270.0,270.0,VESSEL A,,WA001,70,0,,,,,A\n",
    "368000001,2023-01-01T02:00:00,34.01,-118.01,5.0,270.0,270.0,VESSEL A,,WA001,70,0,,,,,A\n",
    "368000002,2023-01-01T00:05:00,33.9,-117.9,0.0,0.0,511.0,VESSEL B,,WB002,30,0,,,,,A\n",
    "368000003,2023-01-01T00:10:00,-10.5,142.1,3.0,90.0,90.0,AUSSIE FISHER,,AF001,30,0,,,,,A\n",
]


def _make_csv(rows=None):
    """Write synthetic NOAA CSV to a temp file and return path."""
    import tempfile, pathlib
    rows = rows or NOAA_ROWS
    content = NOAA_HEADER + "".join(rows)
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w")
    tmp.write(content)
    tmp.close()
    return pathlib.Path(tmp.name)


class TestLoadNoaaCSV:
    def test_basic_load(self):
        path = _make_csv()
        df = load_noaa_csv(path)
        assert len(df) == 4
        assert set(df.columns) >= {"mmsi", "timestamp", "lat", "lon", "sog", "cog", "vessel_name", "vessel_type", "source"}

    def test_source_tag(self):
        path = _make_csv()
        df = load_noaa_csv(path)
        assert (df["source"] == "NOAA_MarineCadastre").all()

    def test_vessel_type_mapped(self):
        path = _make_csv()
        df = load_noaa_csv(path)
        cargo_rows = df[df["vessel_name"] == "VESSEL A"]
        assert (cargo_rows["vessel_type"] == "Cargo").all()
        fishing_rows = df[df["vessel_name"] == "VESSEL B"]
        assert (fishing_rows["vessel_type"] == "Fishing").all()

    def test_bbox_clips_correctly(self):
        path = _make_csv()
        # bbox around Australia only
        df = load_noaa_csv(path, bbox=(95.0, -48.0, 170.0, -4.0))
        assert len(df) == 1
        assert df.iloc[0]["vessel_name"] == "AUSSIE FISHER"

    def test_bbox_empty_result(self):
        path = _make_csv()
        # bbox in middle of nowhere
        df = load_noaa_csv(path, bbox=(0.0, 0.0, 1.0, 1.0))
        assert len(df) == 0

    def test_timestamps_utc(self):
        path = _make_csv()
        df = load_noaa_csv(path)
        assert hasattr(df["timestamp"].dtype, "tz") and str(df["timestamp"].dtype.tz) == "UTC"

    def test_sorted_by_mmsi_timestamp(self):
        path = _make_csv()
        df = load_noaa_csv(path)
        for mmsi, g in df.groupby("mmsi"):
            assert list(g["timestamp"]) == sorted(g["timestamp"])

    def test_missing_position_dropped(self):
        rows = list(NOAA_ROWS) + [
            "368000099,2023-01-01T01:00:00,,,-999,,,,,,70,0,,,,,A\n"  # missing LAT/LON
        ]
        path = _make_csv(rows)
        df = load_noaa_csv(path)
        assert "368000099" not in df["mmsi"].values

    def test_deduplication(self):
        # Same row twice → should appear once
        rows = [NOAA_ROWS[0], NOAA_ROWS[0]]
        path = _make_csv(rows)
        df = load_noaa_csv(path)
        assert len(df) == 1
