import math
import numpy as np

from models.controllers.PIDController import PIDController
from models.wind.WindProfileBuilder import Vel
from models.data.ProbeFeedbackState import ProbeFeedbackState
from models.calibration.CalibrationManager import CalibrationManager
from models.calibration.TurbulenceCalibration import TurbulenceCalibration
from models.data.ControlFeedbackState import ControlFeedbackState
from models.experiment.ExperimentConfig import ExperimentConfig

class TurbulenceControl():
    """Class which handles overall turbulence intensity control under ClosedLoopControlManager.
    This class includes measuring live turbulence intensity, velocity and outputs a response.
    NOTE: Corrective PID controllers on top of a feedforward turbulence PWM gain."""
    def __init__(self, config: ExperimentConfig) -> None:
        """Initialises gains and moving average statistics for reference."""
        self.KP = 200
        self.KI = 0
        self.KD = 0

        self.TAU = 0.7 # moving average coefficient

        self.FEEDFORWARDGAIN = 0.2

        self.controller = None
        self.statistics = MovingAverageStats(0.7, dt = 0.01)

        # self.calibrator = CalibrationManager(config,TurbulenceCalibration)
        # self.calibrator.determine_calibration()

    def update(self) -> None:
        """Function which obtains live velocity, live statistics and generates a turbulence pwm output to ControlFeedbackState."""
        current_velocity = self._get_probe_windspeed()

        # Turbulence sinusoid amplitude PWM control
        self.statistics.update(current_velocity, ControlFeedbackState.dt)
        current_TI_measurement = self.statistics.TI

        turbulence_correction_pwm = self.controller.update(ControlFeedbackState.target_TI, current_TI_measurement, ControlFeedbackState.dt)
        # turbulence_base_pwm = self.calibrator.get_feed_pwm(target=ControlFeedbackState.target_TI,
        #                                                     velocity_component=ControlFeedbackState.velocity_component) * ControlFeedbackState.mean_velocity_pwm * np.sqrt(2)
        turbulence_base_pwm = self.FEEDFORWARDGAIN * ControlFeedbackState.target_TI * ControlFeedbackState.mean_velocity_pwm * np.sqrt(2)
        
        ControlFeedbackState.baseline_turbulence_pwm = turbulence_base_pwm
        ControlFeedbackState.correction_turbulence_pwm = turbulence_correction_pwm

        print(f"VELOCITY: {current_velocity:.2f}m/s - TARGET: {ControlFeedbackState.target_velocity}")
        print(f"TURBULENCE: {current_TI_measurement:.2f} - TARGET: {ControlFeedbackState.target_TI}")

    def refresh_controller(self) -> None:
        self.controller = PIDController(200,0,0,lim=(-30,30))

    def _get_probe_windspeed(self) -> float:
        """Helper function which obtains the currently selected velocity component probe velocity."""
        v_component = ControlFeedbackState.velocity_component
        if v_component == Vel.X:
            return ProbeFeedbackState.windspeed_x
        if v_component == Vel.Y:
            return ProbeFeedbackState.windspeed_y
        if v_component == Vel.Z:
            return ProbeFeedbackState.windspeed_z

class MovingAverageStats():
    """Class which uses exponential moving averages to determine the live turbulence intensity with small delay,
    this class directly is used by TurbulenceControl to get the current measurement."""
    def __init__(self, tau: float, dt: float) -> None:
        self.dt = dt
        self.tau = tau
        self.alpha = math.exp(-dt / tau)

        self.mean = None
        self.var = None

    def update(self, x: float, dt: float) -> None:
        """Function which calculates current exponential filtered change of mean and variance based on prior statistics."""
        self.dt = dt
        self.alpha = math.exp(-dt / self.tau)
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
    def TI(self) -> float:
        """Function which returns the current instantaneous turbulence intensity of the flow"""
        if self.mean is None or self.mean == 0:
            return 0.0
        return math.sqrt(self.var) / self.mean

