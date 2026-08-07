from models.controllers.PIDController import PIDController
from models.calibration.CalibrationManager import CalibrationManager
from models.data.ProbeFeedbackState import ProbeFeedbackState
from models.experiment.ExperimentClock import ExperimentClock
from models.experiment.ExperimentConfig import ExperimentConfig
from models.wind.WindProfileBuilder import Vel, FanInstruction, ControlMode

from collections import deque
import numpy as np

class RollingStats:
    def __init__(self, window_size):
        self.window = deque(maxlen=window_size) #TODO: make this time based

    def update(self, value):
        self.window.append(value)

    @property
    def mean(self):
        # print(f"MEAN {np.mean(self.window)}")
        return np.mean(self.window)
    
    @property
    def std(self):
        # print(f"STD: {np.std(self.window)}")
        return np.std(self.window)

    @property
    def TI(self):
        if self.mean == 0:
            return 0
        # print(f"TI: {self.std /self.mean}")
        return (self.std /self.mean)

class ClosedLoopControlManager():
    def __init__(self, clock: ExperimentClock, config: ExperimentConfig) -> None:
        self.clock = clock
        self.config = config

        self.start_time = self.clock.time_elapsed
        self.start_time = None
        self.current_time = None
        self.time_elapsed = 0
        self.dt = 0

        self.result_pwm = 0
        self.base_velocity_pwm = 0

        # self.calibrator = CalibrationManager(self.config)
        # self.calibrator.determine_calibration()
        self.velocity_controller = PIDController(0.1,0,0.015)
        self.mean_velocity_controller = PIDController(0.1,0,0.015)
        self.TI_controller = PIDController(100,0,0)
        self.rolling_stats = RollingStats(400) # 2 second window

        self.command = None
        self.target_mean_velocity = 0
        self.target_TI = 0

    def change_instr(self, new_command: FanInstruction) -> None:
        self.command = new_command
        self.target_mean_velocity = self.command.velocity
        self.target_TI = self.command.TI/100

    def update(self) -> int:
        self._update_time()
        current_velocity_measurement = self._get_probe_windspeed()
        current_TI_measurement = self.rolling_stats.TI
        # current_vmean_measurement = self.rolling_stats.mean

        # base_pwm = self.calibrator.get_feed_pwm(self.target,"vz")
        if self.time_elapsed >= 15:
            self.rolling_stats.update(current_velocity_measurement)
            # velocity_correction_pwm = self.velocity_controller.update(self.target_mean_velocity, current_vmean_measurement, self.dt)
            ti_correction_pwm = self.TI_controller.update(self.target_TI, current_TI_measurement, self.dt)
            total_correction_pwm = self.base_velocity_pwm + ti_correction_pwm*np.sin(2*np.pi*0.4 * self.time_elapsed) #LOCKED FQ FOR NOW
            self.result_pwm = total_correction_pwm
            print(f"Current TI: {current_TI_measurement}, Target TI: {self.target_TI}, TI correction PWM: {ti_correction_pwm}")
        elif self.time_elapsed < 15:# INITIALISATION
            velocity_correction_pwm = self.velocity_controller.update(self.target_mean_velocity, current_velocity_measurement, self.dt)
            total_correction_pwm = velocity_correction_pwm
            self.result_pwm += total_correction_pwm # external integrator for velocity PID
            self.base_velocity_pwm = self.result_pwm

        result_instruction = FanInstruction(control_mode=ControlMode.PWM,pwm=self.result_pwm)
        return result_instruction

    def _update_time(self) -> None:
        current_time = self.clock.time_elapsed
        if self.start_time is None:
            self.start_time = current_time
            self.current_time = current_time
            self.time_elapsed = 0
            self.dt = 0.05
            return
        self.dt = current_time - self.current_time
        self.current_time = current_time
        self.time_elapsed = current_time - self.start_time

    def _get_probe_windspeed(self) -> float:
        cmd = self.command
        v_component = cmd.velocity_component
        if v_component == Vel.X:
            return ProbeFeedbackState.windspeed_x
        if v_component == Vel.Y:
            return ProbeFeedbackState.windspeed_y
        if v_component == Vel.Z:
            return ProbeFeedbackState.windspeed_z

