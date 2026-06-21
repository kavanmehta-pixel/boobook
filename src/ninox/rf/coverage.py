from __future__ import annotations
import math
from dataclasses import asdict
from ninox.config import TORRES_STRAIT_CLUSTER, ChokePointCluster
from ninox.utils_geo import haversine_km


def radio_horizon_km(antenna_height_m: float, vessel_antenna_height_m: float = 10.0) -> float:
    """Approximate VHF radio horizon over water in km.

    Uses 4.12 * (sqrt(h1) + sqrt(h2)), common engineering approximation.
    """
    return 4.12 * (math.sqrt(max(0, antenna_height_m)) + math.sqrt(max(0, vessel_antenna_height_m)))


def cluster_summary(cluster: ChokePointCluster = TORRES_STRAIT_CLUSTER) -> dict:
    nodes = []
    for n in cluster.nodes:
        nodes.append({**asdict(n), "vhf_horizon_km": radio_horizon_km(n.antenna_height_m)})
    baselines = []
    for i, a in enumerate(cluster.nodes):
        for b in cluster.nodes[i+1:]:
            baselines.append({"from": a.node_id, "to": b.node_id, "distance_km": haversine_km(a.lat, a.lon, b.lat, b.lon)})
    return {"cluster_id": cluster.cluster_id, "name": cluster.name, "description": cluster.description, "nodes": nodes, "baselines": baselines, "tdoa_min_nodes": 3}


def point_node_count(lat: float, lon: float, cluster: ChokePointCluster = TORRES_STRAIT_CLUSTER) -> int:
    count = 0
    for n in cluster.nodes:
        if haversine_km(lat, lon, n.lat, n.lon) <= radio_horizon_km(n.antenna_height_m):
            count += 1
    return count


def tdoa_viable(lat: float, lon: float, cluster: ChokePointCluster = TORRES_STRAIT_CLUSTER) -> bool:
    return point_node_count(lat, lon, cluster) >= 3
