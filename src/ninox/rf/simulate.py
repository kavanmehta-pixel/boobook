from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from ninox.rf.tdoa_solver import make_tdoa, solve_tdoa


def run_rf_simulation(out_dir: str | Path = "artifacts") -> dict:
    """Run a deterministic RF/TDOA planning simulation."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receivers = np.array([[0.0, 0.0], [30_000.0, 2_000.0], [12_000.0, 28_000.0], [38_000.0, 31_000.0]])
    emitter = np.array([18_000.0, 14_000.0])
    tdoa = make_tdoa(receivers, emitter, noise_s=150e-9, seed=7)
    solved = solve_tdoa(receivers, tdoa, timing_sigma_s=300e-9)
    err_m = float(np.linalg.norm(np.array([solved["x_m"], solved["y_m"]]) - emitter))
    result = {"mode": "simulation_only", "receiver_xy_m": receivers.tolist(), "true_emitter_xy_m": emitter.tolist(), "solved": solved, "position_error_m": err_m}
    (out / "rf_simulation_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
