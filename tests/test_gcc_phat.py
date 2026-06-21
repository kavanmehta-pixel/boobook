import numpy as np
from ninox.rf.gcc_phat import gcc_phat


def test_gcc_phat_known_integer_delay():
    fs = 1000
    sig = np.zeros(512); sig[100] = 1
    ref = np.zeros(512); ref[110] = 1
    tau, _ = gcc_phat(sig, ref, fs=fs, max_tau=0.1, interp=1)
    assert abs(tau - (-0.010)) <= 0.001
