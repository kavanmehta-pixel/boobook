import numpy as np
from boobook.rf.tdoa_solver import make_tdoa, solve_tdoa


def test_tdoa_solver_recovers_synthetic_point():
    rx = np.array([[0,0],[30000,0],[0,30000],[30000,30000]], dtype=float)
    emitter = np.array([12000, 17000], dtype=float)
    tdoa = make_tdoa(rx, emitter)
    result = solve_tdoa(rx, tdoa)
    err = np.linalg.norm(np.array([result["x_m"], result["y_m"]]) - emitter)
    assert err < 10
    assert result["success"]
