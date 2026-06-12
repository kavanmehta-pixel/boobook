from __future__ import annotations
import numpy as np
from scipy.optimize import least_squares

C_MPS = 299_792_458.0


def solve_tdoa(receiver_xy_m: np.ndarray, tdoa_s: np.ndarray, initial_xy_m: np.ndarray | None = None, timing_sigma_s: float = 300e-9) -> dict:
    """Least-squares 2D TDOA solve relative to receiver 0.

    receiver_xy_m: Nx2 receiver positions in a local projected frame.
    tdoa_s: N-1 time differences where tdoa[i] = range(receiver i+1)-range(receiver 0) / c.
    """
    rx = np.asarray(receiver_xy_m, dtype=float)
    tdoa = np.asarray(tdoa_s, dtype=float)
    if rx.ndim != 2 or rx.shape[1] != 2 or len(rx) < 3:
        raise ValueError("Need at least three receiver positions with shape Nx2")
    if len(tdoa) != len(rx) - 1:
        raise ValueError("tdoa_s must have length N-1 relative to receiver 0")
    x0 = np.mean(rx, axis=0) if initial_xy_m is None else np.asarray(initial_xy_m, dtype=float)
    range_diffs = tdoa * C_MPS

    def residual(pos):
        ranges = np.linalg.norm(rx - pos, axis=1)
        pred = ranges[1:] - ranges[0]
        return (pred - range_diffs) / max(C_MPS * timing_sigma_s, 1e-6)

    result = least_squares(residual, x0=x0, method="trf")
    residual_m = residual(result.x) * max(C_MPS * timing_sigma_s, 1e-6)
    rms_residual_m = float(np.sqrt(np.mean(residual_m ** 2)))
    cep50_m = float(max(1.0, 1.1774 * C_MPS * timing_sigma_s + rms_residual_m))
    return {"x_m": float(result.x[0]), "y_m": float(result.x[1]), "success": bool(result.success), "rms_residual_m": rms_residual_m, "cep50_m": cep50_m}


def make_tdoa(receiver_xy_m: np.ndarray, emitter_xy_m: np.ndarray, noise_s: float = 0.0, seed: int | None = None) -> np.ndarray:
    rx = np.asarray(receiver_xy_m, dtype=float)
    emitter = np.asarray(emitter_xy_m, dtype=float)
    ranges = np.linalg.norm(rx - emitter, axis=1)
    tdoa = (ranges[1:] - ranges[0]) / C_MPS
    if noise_s:
        rng = np.random.default_rng(seed)
        tdoa = tdoa + rng.normal(0, noise_s, size=tdoa.shape)
    return tdoa
