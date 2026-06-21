"""Tests for AMSA CTS shapefile ingestor."""
import tempfile
import pathlib
import pytest
import pandas as pd

# geopandas required — skip whole module if not installed
gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point


def _make_shp(rows: list[dict], tmp_path: pathlib.Path) -> pathlib.Path:
    """Write a minimal shapefile with AMSA CTS schema."""
    import geopandas as gpd
    from shapely.geometry import Point

    gdf = gpd.GeoDataFrame(rows, geometry=[Point(r["LON"], r["LAT"]) for r in rows], crs="EPSG:4326")
    shp_path = tmp_path / "test_cts.shp"
    gdf.to_file(shp_path)
    return shp_path


SAMPLE_ROWS = [
    {"CRAFT_ID": 503001001, "LON": 142.1,  "LAT": -10.5, "COURSE": 90.0,  "SPEED": 5.0,  "TYPE": "Fishing",              "SUBTYPE": None, "LENGTH": 20, "BEAM": 5, "DRAUGHT": 2.0, "TIMESTAMP": "16/05/2026 11:22:47 AM"},
    {"CRAFT_ID": 503001002, "LON": 142.5,  "LAT": -10.8, "COURSE": 180.0, "SPEED": 12.0, "TYPE": "Cargo ship - All",       "SUBTYPE": None, "LENGTH": 150,"BEAM":25, "DRAUGHT": 8.0, "TIMESTAMP": "16/05/2026 12:00:00 PM"},
    {"CRAFT_ID": 503001003, "LON": 143.0,  "LAT": -11.0, "COURSE": 0.0,   "SPEED": 0.5,  "TYPE": "Law enforcement",        "SUBTYPE": None, "LENGTH": 45, "BEAM":8,  "DRAUGHT": 3.0, "TIMESTAMP": "16/05/2026 1:30:00 PM"},
    {"CRAFT_ID": 503001001, "LON": 142.15, "LAT": -10.52,"COURSE": 90.0,  "SPEED": 5.0,  "TYPE": "Fishing",              "SUBTYPE": None, "LENGTH": 20, "BEAM": 5, "DRAUGHT": 2.0, "TIMESTAMP": "16/05/2026 2:00:00 PM"},
    # Negative CRAFT_ID — should be filtered
    {"CRAFT_ID": -2146018332, "LON": 142.2, "LAT": -10.6, "COURSE": 45.0, "SPEED": 8.0, "TYPE": "Unknown",              "SUBTYPE": None, "LENGTH": 0,  "BEAM": 0, "DRAUGHT": 0.0, "TIMESTAMP": "16/05/2026 3:00:00 PM"},
    # Outside Torres Strait bbox
    {"CRAFT_ID": 503001099, "LON": 151.2,  "LAT": -33.8, "COURSE": 270.0, "SPEED": 15.0, "TYPE": "Cargo ship - All",      "SUBTYPE": None, "LENGTH": 200,"BEAM":30, "DRAUGHT":10.0, "TIMESTAMP": "16/05/2026 4:00:00 PM"},
    # 2022-style timestamp
    {"CRAFT_ID": 503001004, "LON": 142.3,  "LAT": -10.7, "COURSE": 120.0, "SPEED": 3.0,  "TYPE": "Fishing",              "SUBTYPE": None, "LENGTH": 18, "BEAM": 4, "DRAUGHT": 1.5, "TIMESTAMP": "2/12/2022 5:06:00 PM"},
]


class TestLoadAMSAShp:
    def test_basic_load(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        shp = _make_shp(SAMPLE_ROWS, tmp_path)
        df = load_amsa_shp(shp)
        # Should have all rows except the negative CRAFT_ID one
        assert len(df) >= len(SAMPLE_ROWS) - 1
        assert set(df.columns) >= {"mmsi","timestamp","lat","lon","sog","cog","vessel_name","vessel_type","source"}

    def test_negative_craft_id_filtered(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        shp = _make_shp(SAMPLE_ROWS, tmp_path)
        df = load_amsa_shp(shp)
        assert not df["mmsi"].str.startswith("-").any()

    def test_bbox_clips(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        shp = _make_shp(SAMPLE_ROWS, tmp_path)
        # Torres Strait only
        df = load_amsa_shp(shp, bbox=(141.0, -11.5, 144.5, -8.5))
        # Sydney row (151.2, -33.8) should be excluded
        assert not ((df["lon"] > 150).any())

    def test_vessel_type_mapped(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        shp = _make_shp(SAMPLE_ROWS, tmp_path)
        df = load_amsa_shp(shp)
        types = df["vessel_type"].unique()
        assert "Fishing" in types
        assert "Cargo" in types
        assert "Law_enforcement" in types
        # Should not have raw AMSA strings
        assert "Cargo ship - All" not in types
        assert "Law enforcement" not in types

    def test_timestamps_utc(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        shp = _make_shp(SAMPLE_ROWS, tmp_path)
        df = load_amsa_shp(shp)
        assert hasattr(df["timestamp"].dtype, "tz")
        assert str(df["timestamp"].dtype.tz) == "UTC"

    def test_both_timestamp_formats_parsed(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        shp = _make_shp(SAMPLE_ROWS, tmp_path)
        df = load_amsa_shp(shp)
        # Both 2026 and 2022 format rows should parse without NaT
        assert df["timestamp"].isna().sum() == 0

    def test_source_tag(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        shp = _make_shp(SAMPLE_ROWS, tmp_path)
        df = load_amsa_shp(shp, month_label="2026-05")
        assert (df["source"] == "AMSA_CTS_2026-05").all()

    def test_sorted_by_mmsi_timestamp(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        shp = _make_shp(SAMPLE_ROWS, tmp_path)
        df = load_amsa_shp(shp)
        for mmsi, g in df.groupby("mmsi"):
            assert list(g["timestamp"]) == sorted(g["timestamp"])

    def test_directory_input(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        _make_shp(SAMPLE_ROWS, tmp_path)
        # Pass directory instead of .shp path
        df = load_amsa_shp(tmp_path)
        assert len(df) > 0

    def test_empty_bbox_returns_empty(self, tmp_path):
        from ninox.ingest.amsa_shp import load_amsa_shp
        shp = _make_shp(SAMPLE_ROWS, tmp_path)
        df = load_amsa_shp(shp, bbox=(0.0, 0.0, 1.0, 1.0))
        assert len(df) == 0
        assert list(df.columns) == ["mmsi","timestamp","lat","lon","sog","cog","vessel_name","vessel_type","source"]
