from __future__ import annotations
import numpy as np


def gcc_phat(sig: np.ndarray, refsig: np.ndarray, fs: float = 1.0, max_tau: float | None = None, interp: int = 16) -> tuple[float, np.ndarray]:
    """Estimate time delay using GCC-PHAT.

    Returns (tau_seconds, cross_correlation).
    Positive tau means `sig` lags `refsig`.
    """
    sig = np.asarray(sig)
    refsig = np.asarray(refsig)
    n = sig.shape[0] + refsig.shape[0]
    SIG = np.fft.rfft(sig, n=n)
    REFSIG = np.fft.rfft(refsig, n=n)
    R = SIG * np.conj(REFSIG)
    R /= np.abs(R) + np.finfo(float).eps
    cc = np.fft.irfft(R, n=interp * n)
    max_shift = int(interp * n / 2)
    if max_tau is not None:
        max_shift = min(max_shift, int(interp * fs * max_tau))
    cc = np.concatenate((cc[-max_shift:], cc[:max_shift + 1]))
    shift = int(np.argmax(np.abs(cc)) - max_shift)
    tau = shift / float(interp * fs)
    return tau, cc
