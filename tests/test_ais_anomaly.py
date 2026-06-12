"""Tests for AIS anomaly detection rules."""
import pandas as pd
import pytest
from boobook.analytics.ais_anomaly import (
    detect_gaps, detect_impossible_speed, detect_loitering,
    detect_rendezvous, detect_sensitive_zone, run_validation,
)

def _df(rows):
    df = pd.DataFrame(rows, columns=["mmsi","timestamp","lat","lon","sog","cog","vessel_name","vessel_type","source"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df

# ── Gap detection ──────────────────────────────────────────────────────────
class TestGaps:
    def test_detects_gap_over_threshold(self):
        df = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,10,90,"A","Fishing","t"],
            ["503001","2026-01-01T05:00:00Z",-10.6,142.2,10,90,"A","Fishing","t"],
        ])
        alerts = detect_gaps(df, threshold_hours=2.0)
        assert len(alerts) == 1
        assert alerts[0].alert_type == "AIS_GAP"
        assert alerts[0].risk_score >= 55

    def test_no_alert_below_threshold(self):
        df = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,10,90,"A","Cargo","t"],
            ["503001","2026-01-01T01:00:00Z",-10.5,142.2,10,90,"A","Cargo","t"],
        ])
        assert len(detect_gaps(df, threshold_hours=2.0)) == 0

    def test_fishing_vessel_higher_score_than_cargo(self):
        def make(vtype):
            return _df([
                ["503001","2026-01-01T00:00:00Z",-10.5,142.1,10,90,"A",vtype,"t"],
                ["503001","2026-01-01T04:00:00Z",-10.5,142.2,10,90,"A",vtype,"t"],
            ])
        fishing_score = detect_gaps(make("Fishing"), threshold_hours=2.0)[0].risk_score
        cargo_score = detect_gaps(make("Cargo"), threshold_hours=2.0)[0].risk_score
        assert fishing_score >= cargo_score

    def test_multiple_gaps_same_vessel(self):
        df = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,10,90,"A","Fishing","t"],
            ["503001","2026-01-01T05:00:00Z",-10.5,142.1,10,90,"A","Fishing","t"],
            ["503001","2026-01-01T12:00:00Z",-10.5,142.1,10,90,"A","Fishing","t"],
        ])
        alerts = detect_gaps(df, threshold_hours=2.0)
        assert len(alerts) == 2


# ── Impossible speed ────────────────────────────────────────────────────────
class TestImpossibleSpeed:
    def test_detects_teleport(self):
        df = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,10,90,"A","Cargo","t"],
            ["503001","2026-01-01T00:30:00Z",-12.0,144.0,10,90,"A","Cargo","t"],  # ~200 kn
        ])
        alerts = detect_impossible_speed(df, max_implied_knots=45.0)
        assert len(alerts) == 1
        assert alerts[0].risk_score >= 70

    def test_normal_speed_no_alert(self):
        df = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,10,90,"A","Cargo","t"],
            ["503001","2026-01-01T01:00:00Z",-10.52,142.18,10,90,"A","Cargo","t"],
        ])
        assert len(detect_impossible_speed(df)) == 0

    def test_score_scales_with_speed(self):
        def make_jump(dlat):
            return _df([
                ["503001","2026-01-01T00:00:00Z",-10.5,142.1,10,90,"A","Cargo","t"],
                ["503001","2026-01-01T00:30:00Z",-10.5+dlat,142.1,10,90,"A","Cargo","t"],
            ])
        a_small = detect_impossible_speed(make_jump(1.0))
        a_big = detect_impossible_speed(make_jump(3.0))
        if a_small and a_big:
            assert a_big[0].risk_score >= a_small[0].risk_score


# ── Loitering ───────────────────────────────────────────────────────────────
class TestLoitering:
    def test_detects_loitering(self):
        rows = [
            ["503001", f"2026-01-01T0{i}:00:00Z", -10.50 + i*0.001, 142.10 + i*0.001, 1.0, 10, "FISHBOAT", "Fishing", "t"]
            for i in range(8)
        ]
        df = _df(rows)
        alerts = detect_loitering(df, min_hours=2.0, radius_km=5.0)
        assert len(alerts) == 1
        assert alerts[0].alert_type == "LOITERING"

    def test_moving_vessel_not_loitering(self):
        rows = [
            ["503001", f"2026-01-01T0{i}:00:00Z", -10.0 + i*0.5, 142.0, 12.0, 0, "FAST", "Cargo", "t"]
            for i in range(5)
        ]
        df = _df(rows)
        assert len(detect_loitering(df)) == 0

    def test_too_short_span_no_alert(self):
        rows = [
            ["503001", f"2026-01-01T00:{i*10:02d}:00Z", -10.50, 142.10, 0.5, 0, "SLOW", "Fishing", "t"]
            for i in range(6)
        ]
        df = _df(rows)
        assert len(detect_loitering(df, min_hours=2.0)) == 0


# ── Rendezvous ──────────────────────────────────────────────────────────────
class TestRendezvous:
    def test_detects_close_pair(self):
        df = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,5,90,"A","Fishing","t"],
            ["503002","2026-01-01T00:10:00Z",-10.501,142.101,5,90,"B","Fishing","t"],
        ])
        alerts = detect_rendezvous(df, window_minutes=30, distance_km=2.0)
        assert len(alerts) == 1
        assert "503001" in alerts[0].mmsi or "503002" in alerts[0].mmsi

    def test_both_fishing_higher_score(self):
        df_fishing = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,5,90,"A","Fishing","t"],
            ["503002","2026-01-01T00:05:00Z",-10.501,142.101,5,90,"B","Fishing","t"],
        ])
        df_mixed = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,5,90,"A","Fishing","t"],
            ["503002","2026-01-01T00:05:00Z",-10.501,142.101,5,90,"B","Cargo","t"],
        ])
        fishing_alerts = detect_rendezvous(df_fishing)
        mixed_alerts = detect_rendezvous(df_mixed)
        if fishing_alerts and mixed_alerts:
            assert fishing_alerts[0].risk_score >= mixed_alerts[0].risk_score

    def test_patrol_vessel_excluded(self):
        df = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,18,90,"PATROL","Law Enforcement","t"],
            ["503002","2026-01-01T00:05:00Z",-10.501,142.101,5,90,"FISHBOAT","Fishing","t"],
        ])
        alerts = detect_rendezvous(df)
        assert len(alerts) == 0

    def test_no_alert_when_far_apart(self):
        df = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,5,90,"A","Fishing","t"],
            ["503002","2026-01-01T00:05:00Z",-11.0,143.0,5,90,"B","Fishing","t"],
        ])
        assert len(detect_rendezvous(df, distance_km=2.0)) == 0

    def test_no_self_rendezvous(self):
        df = _df([
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,1,0,"A","Fishing","t"],
            ["503001","2026-01-01T00:10:00Z",-10.501,142.101,1,0,"A","Fishing","t"],
        ])
        assert len(detect_rendezvous(df)) == 0


# ── Sensitive zone ──────────────────────────────────────────────────────────
class TestSensitiveZone:
    def test_detects_zone_entry(self):
        df = _df([["503001","2026-01-01T00:00:00Z",-10.36,142.52,5,0,"A","Fishing","t"]])
        zones = [{"name":"TestZone","lat":-10.35,"lon":142.52,"radius_km":10.0}]
        alerts = detect_sensitive_zone(df, zones=zones)
        assert len(alerts) == 1

    def test_outside_zone_no_alert(self):
        df = _df([["503001","2026-01-01T00:00:00Z",-15.0,145.0,5,0,"A","Fishing","t"]])
        zones = [{"name":"TestZone","lat":-10.35,"lon":142.52,"radius_km":10.0}]
        assert len(detect_sensitive_zone(df, zones=zones)) == 0


# ── Integration ─────────────────────────────────────────────────────────────
class TestIntegration:
    def test_run_validation_all_types_present(self):
        from boobook.ingest.amsa_cts import normalise_file
        import pathlib
        sample = pathlib.Path("data/sample/sample_ais_events.csv")
        if not sample.exists():
            pytest.skip("sample data not found")
        df = normalise_file(sample)
        alerts_df, vessels_df, tracks, summary = run_validation(df)
        types = set(alerts_df["alert_type"])
        assert "AIS_GAP" in types
        assert "IMPOSSIBLE_SPEED" in types
        assert "LOITERING" in types
        assert "RENDEZVOUS_CANDIDATE" in types
        assert summary["vessels"] > 0
        assert tracks["type"] == "FeatureCollection"

    def test_empty_dataframe_safe(self):
        import pandas as pd
        empty = pd.DataFrame(columns=["mmsi","timestamp","lat","lon","sog","cog","vessel_name","vessel_type","source"])
        alerts, vessels, tracks, summary = run_validation(empty)
        assert summary["alerts"] == 0

    def test_malformed_csv_handled(self, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text("mmsi,timestamp,lat,lon\nNOT_A_NUMBER,bad_ts,bad_lat,bad_lon\n")
        from boobook.ingest.amsa_cts import normalise_file
        df = normalise_file(f)
        assert len(df) == 0  # all rows dropped — bad numeric / OOB bounds

    def test_outputs_written(self, tmp_path):
        from boobook.analytics.ais_anomaly import write_validation_outputs
        rows = [
            ["503001","2026-01-01T00:00:00Z",-10.5,142.1,10,90,"A","Cargo","t"],
            ["503001","2026-01-01T06:00:00Z",-10.6,142.2,10,90,"A","Cargo","t"],
        ]
        df = _df(rows)
        paths = write_validation_outputs(df, tmp_path)
        import pathlib
        for key in ("normalised","alerts","vessels","tracks","summary"):
            assert pathlib.Path(paths[key]).exists()
