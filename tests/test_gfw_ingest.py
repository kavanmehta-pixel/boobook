"""Tests for Global Fishing Watch events ingestor."""
import pathlib
import tempfile
import pandas as pd
import pytest
from ninox.ingest.gfw_events import load_gfw_events, GFW_COLUMNS


def _make_gfw_csv(content: str) -> pathlib.Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w")
    tmp.write(content)
    tmp.close()
    return pathlib.Path(tmp.name)


AIS_OFF_CSV = """\
vessel_mmsi,start,end,lat,lon,vessel_flag,vessel_type
503001001,2023-01-01T00:00:00Z,2023-01-01T06:00:00Z,-10.5,142.1,AUS,fishing
503001002,2023-01-01T02:00:00Z,2023-01-01T14:00:00Z,-10.8,141.9,IDN,fishing
503001003,2023-01-01T04:00:00Z,2023-01-01T05:00:00Z,-33.8,151.2,AUS,cargo
"""

ENCOUNTER_CSV = """\
mmsi,start,end,mean_latitude,mean_longitude,iso3
503001001,2023-06-01T10:00:00Z,2023-06-01T10:30:00Z,-10.5,142.1,AUS
503001004,2023-06-01T10:05:00Z,2023-06-01T10:35:00Z,-10.51,142.11,CHN
"""


class TestLoadGFWEvents:
    def test_basic_load_ais_off(self):
        path = _make_gfw_csv(AIS_OFF_CSV)
        df = load_gfw_events(path, event_type="ais_off")
        assert len(df) == 3
        assert set(df.columns) == set(GFW_COLUMNS)

    def test_event_type_tag(self):
        path = _make_gfw_csv(AIS_OFF_CSV)
        df = load_gfw_events(path, event_type="ais_off")
        assert (df["event_type"] == "ais_off").all()

    def test_duration_computed(self):
        path = _make_gfw_csv(AIS_OFF_CSV)
        df = load_gfw_events(path, event_type="ais_off")
        first = df.iloc[0]
        assert abs(first["duration_hours"] - 6.0) < 0.01

    def test_source_tag(self):
        path = _make_gfw_csv(AIS_OFF_CSV)
        df = load_gfw_events(path, event_type="ais_off")
        assert (df["source"] == "GFW_ais_off").all()

    def test_bbox_clips(self):
        path = _make_gfw_csv(AIS_OFF_CSV)
        # Torres Strait only
        df = load_gfw_events(path, event_type="ais_off", bbox=(141.0, -11.5, 144.5, -8.5))
        assert len(df) == 2
        assert "503001003" not in df["mmsi"].values  # Sydney vessel excluded

    def test_alternative_column_names(self):
        """mmsi/mean_latitude/mean_longitude variant (encounter format)."""
        path = _make_gfw_csv(ENCOUNTER_CSV)
        df = load_gfw_events(path, event_type="encounter")
        assert len(df) == 2
        assert set(df["mmsi"].values) == {"503001001", "503001004"}

    def test_timestamps_utc(self):
        path = _make_gfw_csv(AIS_OFF_CSV)
        df = load_gfw_events(path, event_type="ais_off")
        assert "UTC" in str(df["start"].dtype)

    def test_missing_mmsi_dropped(self):
        csv = "vessel_mmsi,start,end,lat,lon,vessel_flag,vessel_type\n"
        csv += ",2023-01-01T00:00:00Z,2023-01-01T06:00:00Z,-10.5,142.1,AUS,fishing\n"
        path = _make_gfw_csv(csv)
        df = load_gfw_events(path, event_type="ais_off")
        assert len(df) == 0

    def test_empty_file(self):
        csv = "vessel_mmsi,start,end,lat,lon,vessel_flag,vessel_type\n"
        path = _make_gfw_csv(csv)
        df = load_gfw_events(path, event_type="ais_off")
        assert len(df) == 0
        assert list(df.columns) == GFW_COLUMNS
