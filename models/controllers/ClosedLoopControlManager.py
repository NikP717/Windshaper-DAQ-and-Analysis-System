from models.controllers.PIDController import PIDController
from models.calibration.CalibrationManager import CalibrationManager
from models.data.ProbeFeedbackState import ProbeFeedbackState

class ClosedLoopControlManager():
    def __init__(self, clock, config):
        self.clock = clock
        self.config = config

        self.current_time = 0
        self.dt = 0

        self.calibrator = CalibrationManager(self.config)
        self.calibrator.determine_calibration()
    
        self.controller = PIDController()
        self.target = None

        self.MAX_PWM = 60

    def change_instr(self, new_command):
        self.current_time = self.clock.time_elapsed
        self.target = new_command

    def update(self) -> int:
        current_measurement = ProbeFeedbackState.windspeed_z # NOTE: ONLY WORKS FOR Z VELOCITY RN 
        self._update_dt()
        base_pwm = self.calibrator.get_feed_pwm(self.target,"vz")
        correction_pwm = self.controller.update(self.target, current_measurement, self.dt)
        result_pwm = base_pwm + correction_pwm

        if result_pwm > self.MAX_PWM: # safety limit for now
            return self.MAX_PWM
        return result_pwm

    def _update_dt(self):
        current_time = self.clock.time_elapsed
        self.dt = current_time - self.current_time
        self.current_time = current_time
