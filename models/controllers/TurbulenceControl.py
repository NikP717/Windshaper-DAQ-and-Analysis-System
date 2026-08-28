from models.controllers.PIDController import PIDController
from models.wind.WindProfileBuilder import Vel
from models.data.ProbeFeedbackState import ProbeFeedbackState
from models.calibration.CalibrationManager import CalibrationManager
from models.calibration.TurbulenceCalibration import TurbulenceCalibration
from models.data.ControlFeedbackState import ControlFeedbackState
from models.experiment.ExperimentConfig import ExperimentConfig

import math
import numpy as np

class TurbulenceControl():
    def __init__(self, config: ExperimentConfig):
        # Note: Corrective PID for feedforward baseline turbulence PWM obtained from calibrator
        self.KP = 200
        self.KI = 0
        self.KD = 0

        self.TAU = 0.7 # moving average coefficient

        self.controller = None
        self.statistics = MovingAverageStats(0.7, dt = 0.01)

        self.calibrator = CalibrationManager(config,TurbulenceCalibration)
        self.calibrator.determine_calibration()

    def update(self):
        current_velocity = self._get_probe_windspeed()

        # Turbulence sinusoid amplitude PWM control
        self.statistics.update(current_velocity, ControlFeedbackState.dt)
        current_TI_measurement = self.statistics.TI

        turbulence_correction_pwm = self.controller.update(ControlFeedbackState.target_TI, current_TI_measurement, ControlFeedbackState.dt)
        # Sqrt 2 because RMS PWM fluctuation analogous to turbulence
        turbulence_base_pwm = self.calibrator.get_feed_pwm(target=ControlFeedbackState.target_TI,
                                                            velocity_component=ControlFeedbackState.velocity_component) * ControlFeedbackState.mean_velocity_pwm * np.sqrt(2)
        
        ControlFeedbackState.baseline_turbulence_pwm = turbulence_base_pwm
        ControlFeedbackState.correction_turbulence_pwm = turbulence_correction_pwm

        print(f"VELOCITY: {current_velocity:.2f}m/s - TARGET: {ControlFeedbackState.target_velocity}")
        print(f"TURBULENCE: {current_TI_measurement:.2f} - TARGET: {ControlFeedbackState.target_TI}")

    def refresh_controller(self):
        self.controller = PIDController(200,0,0,lim=(-30,30))

    def _get_probe_windspeed(self) -> float:
        v_component = ControlFeedbackState.velocity_component
        if v_component == Vel.X:
            return ProbeFeedbackState.windspeed_x
        if v_component == Vel.Y:
            return ProbeFeedbackState.windspeed_y
        if v_component == Vel.Z:
            return ProbeFeedbackState.windspeed_z

class MovingAverageStats():
    def __init__(self, tau, dt):
        self.dt = dt
        self.tau = tau
        self.alpha = math.exp(-dt / tau)

        self.mean = None
        self.var = None

    def update(self, x, dt):
        self.dt = dt
        if math.isnan(x):
            return

        # First sample initializes the stats
        if self.mean is None:
            self.mean = x
            self.var = 0.0
            return

        # Exponential weighted mean
        prev_mean = self.mean
        self.mean = self.alpha * self.mean + (1 - self.alpha) * x

        # Exponential weighted variance
        self.var = self.alpha * (self.var + (1 - self.alpha) * (x - prev_mean)**2)

    @property
    def TI(self):
        if self.mean is None or self.mean == 0:
            return 0.0
        return math.sqrt(self.var) / self.mean

