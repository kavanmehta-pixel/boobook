from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class SensorNode:
    node_id: str
    name: str
    lat: float
    lon: float
    antenna_height_m: float = 30.0

@dataclass(frozen=True)
class ChokePointCluster:
    cluster_id: str
    name: str
    description: str
    nodes: tuple[SensorNode, ...]

TORRES_STRAIT_CLUSTER = ChokePointCluster(
    cluster_id="torres_strait_alpha",
    name="Torres Strait Alpha",
    description="Illustrative 3-node choke-point cluster. Planning simulation only, not a deployed network.",
    nodes=(
        SensorNode("TI", "Thursday Island", -10.5833, 142.2183, 38),
        SensorNode("POW", "Prince of Wales Island", -10.6830, 142.1800, 45),
        SensorNode("MUA", "Mua Island", -10.2500, 142.3750, 36),
    ),
)

SENSITIVE_ZONES = [
    {"zone_id": "TS_FISHERY", "name": "Torres Strait illustrative fisheries focus area", "lat": -10.50, "lon": 142.20, "radius_km": 80},
    {"zone_id": "NW_APPROACH", "name": "North-west illustrative patrol corridor", "lat": -13.50, "lon": 124.50, "radius_km": 120},
]
