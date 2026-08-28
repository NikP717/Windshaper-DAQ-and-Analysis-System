from models.controllers.PIDController import PIDController
from models.wind.WindProfileBuilder import Vel
from models.data.ProbeFeedbackState import ProbeFeedbackState
from models.data.ControlFeedbackState import ControlFeedbackState

class VelocityControl():
    def __init__(self):
        # Note: Currently External integrated controller
        self.KP = 0.1
        self.KI = 0
        self.KD = 0.015
        
        self.controller = None

    def update(self):
        current_velocity = self._get_probe_windspeed()
        correction_pwm = self.controller.update(ControlFeedbackState.target_velocity, current_velocity, ControlFeedbackState.dt) 
        ControlFeedbackState.mean_velocity_pwm += correction_pwm # external integrated controller

    def refresh_controller(self):
        self.controller = PIDController(self.KP, self.KI, self.KD)

    def _get_probe_windspeed(self) -> float:
        v_component = ControlFeedbackState.velocity_component
        if v_component == Vel.X:
            return ProbeFeedbackState.windspeed_x
        if v_component == Vel.Y:
            return ProbeFeedbackState.windspeed_y
        if v_component == Vel.Z:
            return ProbeFeedbackState.windspeed_z
        