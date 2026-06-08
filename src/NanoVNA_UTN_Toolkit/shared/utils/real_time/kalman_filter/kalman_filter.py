from filterpy.kalman import KalmanFilter
import numpy as np
import logging

class SParameterKalman:
    def __init__(self, process_noise=0.0001, measurement_noise=10.0):
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self._last_x = 0.0 
        self._init_filter()

    def _init_filter(self):
        self.kf = KalmanFilter(dim_x=1, dim_z=1)
        self.kf.x = np.array([[self._last_x]])
        self.kf.F = np.array([[1.]])
        self.kf.H = np.array([[1.]])
        self.kf.P = np.array([[getattr(self, '_last_P', 100.0)]]) 
        self.kf.R = self.measurement_noise
        self.kf.Q = self.process_noise

    def reset(self):
        self._last_x = float(self.kf.x[0])
        self._last_P = float(self.kf.P[0, 0]) 
        self._init_filter()

    def update(self, value):
        self.kf.predict()
        self.kf.update(np.array([[value]]))
        self._last_x = float(self.kf.x[0])
        return self._last_x

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