from filterpy.kalman import KalmanFilter
import numpy as np

class SParameterKalman:
    def __init__(self, process_noise=0.0001, measurement_noise=10.0):
        self.kf = KalmanFilter(dim_x=1, dim_z=1)

        self.kf.x = np.array([[0.]])
        self.kf.F = np.array([[1.]])
        self.kf.H = np.array([[1.]])

        self.kf.P *= 100
        self.kf.R = measurement_noise
        self.kf.Q = process_noise

    def update(self, value):
        self.kf.predict()
        self.kf.update(np.array([[value]]))
        return float(self.kf.x[0])
    
class ComplexKalman:
    def __init__(self):
        self.kf_real = SParameterKalman()
        self.kf_imag = SParameterKalman()

    def update(self, value: complex):
        r = self.kf_real.update(np.real(value))
        i = self.kf_imag.update(np.imag(value))
        return r + 1j * i