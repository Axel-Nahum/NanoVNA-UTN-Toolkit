from __future__ import annotations

from collections import deque

import numpy as np


class TemporalKalman:
    """One ComplexKalman filter per frequency point, updated sweep-by-sweep.

    Unlike the frequency-domain Kalman (which iterates over frequency points
    within a single sweep treating the index as "time"), this keeps N_freqs
    independent filters that each track the same frequency point across
    successive sweeps — the correct temporal use of Kalman smoothing.
    """

    def __init__(self, n_freqs: int, process_noise: float, measurement_noise: float) -> None:
        from NanoVNA_UTN_Toolkit.shared.utils.real_time.kalman_filter.kalman_filter import ComplexKalman
        self._Q = process_noise
        self._R = measurement_noise
        self._filters = [ComplexKalman(process_noise, measurement_noise) for _ in range(n_freqs)]
        self._n = n_freqs

    def update(self, data: np.ndarray) -> np.ndarray:
        if len(data) != self._n:
            self._reinit(len(data))
        return np.array([f.update(complex(x)) for f, x in zip(self._filters, data)])

    def reset(self) -> None:
        from NanoVNA_UTN_Toolkit.shared.utils.real_time.kalman_filter.kalman_filter import ComplexKalman
        self._filters = [ComplexKalman(self._Q, self._R) for _ in range(self._n)]

    def _reinit(self, n_freqs: int) -> None:
        from NanoVNA_UTN_Toolkit.shared.utils.real_time.kalman_filter.kalman_filter import ComplexKalman
        self._n = n_freqs
        self._filters = [ComplexKalman(self._Q, self._R) for _ in range(n_freqs)]


class TemporalBuffer:
    """Circular buffer of the last *max_sweeps* arrays; push() returns their mean.

    Works with real or complex ndarray — mean is computed element-wise so both
    Re and Im are averaged independently without any conversion step.
    """

    def __init__(self, max_sweeps: int = 10) -> None:
        self._buf: deque[np.ndarray] = deque(maxlen=max(1, max_sweeps))

    # ------------------------------------------------------------------
    def push(self, data: np.ndarray) -> np.ndarray:
        self._buf.append(data.copy())
        return np.mean(np.stack(list(self._buf), axis=0), axis=0)

    def reset(self) -> None:
        self._buf.clear()

    def resize(self, max_sweeps: int) -> None:
        max_sweeps = max(1, max_sweeps)
        if max_sweeps == self._buf.maxlen:
            return
        self._buf = deque(list(self._buf)[-max_sweeps:], maxlen=max_sweeps)

    # ------------------------------------------------------------------
    @property
    def fill(self) -> int:
        return len(self._buf)

    @property
    def capacity(self) -> int:
        return self._buf.maxlen  # type: ignore[return-value]
