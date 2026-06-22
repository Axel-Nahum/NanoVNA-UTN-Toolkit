from filterpy.kalman import KalmanFilter
import numpy as np


class SParameterKalman:

    def __init__(self, process_noise=0.0001, measurement_noise=10.0):
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise

        self.initialized = False

        self._init_filter()

    def _init_filter(self):
        self.kf = KalmanFilter(dim_x=1, dim_z=1)

        self.kf.x = np.array([[100.]])     # estado inicial
        self.kf.F = np.array([[1.]])
        self.kf.H = np.array([[1.]])
        self.kf.P = np.array([[100.]])   # incertidumbre inicial grande

        self.kf.R = self.measurement_noise
        self.kf.Q = self.process_noise

    # -------------------------
    # SUPER RESET (factory reset)
    # -------------------------
    def reset(self):
        self.initialized = False
        self._init_filter()

    def update(self, value):

        # primera muestra = inicialización estable
        if not self.initialized:
            #self.kf.x = np.array([[value]])
            self.initialized = True
            return float(value)

        self.kf.predict()
        self.kf.update(np.array([[value]]))

        # self.kf.x has shape (1, 1); self.kf.x[0] is a 1-D array, and float() of a
        # non-0-d array raises TypeError in NumPy >= 2.0. Index the scalar directly.
        return float(self.kf.x[0, 0])

class ComplexKalman:

    def __init__(self, process_noise=0.0001, measurement_noise=10.0):
        self.kf_real = SParameterKalman(process_noise, measurement_noise)
        self.kf_imag = SParameterKalman(process_noise, measurement_noise)

    def reset(self):
        self.kf_real.reset()
        self.kf_imag.reset()

    def update(self, value: complex):
        r = self.kf_real.update(np.real(value))
        i = self.kf_imag.update(np.imag(value))
        return r + 1j * i