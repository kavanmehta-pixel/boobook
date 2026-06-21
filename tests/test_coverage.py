from ninox.rf.coverage import radio_horizon_km, cluster_summary, tdoa_viable


def test_radio_horizon_positive():
    assert 30 < radio_horizon_km(30, 10) < 50


def test_cluster_summary_has_three_nodes():
    s = cluster_summary()
    assert len(s["nodes"]) == 3
    assert s["tdoa_min_nodes"] == 3


def test_tdoa_viability_boolean():
    assert isinstance(tdoa_viable(-10.55, 142.25), bool)
