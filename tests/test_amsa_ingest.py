import pandas as pd
from boobook.ingest.amsa_cts import normalise_dataframe


def test_normalise_dataframe_aliases_and_bounds():
    raw = pd.DataFrame({
        "MMSI": ["503000001", "bad"],
        "BaseDateTime": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        "Latitude": [-10.5, 55.0],
        "Longitude": [142.2, 10.0],
        "SOG": [10, 5],
        "COG": [90, 90],
        "VesselName": ["Test", "Outside"],
    })
    out = normalise_dataframe(raw)
    assert list(out.columns) == ["mmsi", "timestamp", "lat", "lon", "sog", "cog", "vessel_name", "vessel_type", "source"]
    assert len(out) == 1
    assert out.iloc[0]["mmsi"] == "503000001"
