from math import sin, pi
from typing import Self
import numpy as np

from models.wind.WindProfileBuilder import FanInstruction, ControlMode, FanSelection
from models.data.ControlFeedbackState import ControlFeedbackState
from models.controllers.PIDController import PIDController

class ControlWindFunction():
    def __init__(self):
        self.sine_sum_1 = LiveSineSumWindFunction()
        self.sine_sum_2 = LiveSineSumWindFunction()
        self.sine_sum_2.add_phase_offset(-pi)

    def init(self) -> list[list[FanSelection, FanInstruction]]:
        sine_sum_1 = self.sine_sum_1
        sine_sum_2 = self.sine_sum_2
        selection1 = FanSelection(fans=[1,3,5,7,9], parity="even")
        selection11 = FanSelection(fans=[2,4,6,8], parity="odd")
        selection2 = FanSelection(fans=[1,3,5,7,9], parity="odd")
        selection22 = FanSelection(fans=[2,4,6,8], parity="even")

        instruction1 = FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_sum_1)
        instruction2 = FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_sum_2)
        self.control_init = True
        return [[selection1, instruction1], [selection11, instruction1], [selection2, instruction2], [selection22, instruction2]]

class LiveSineSumWindFunction():
    """Class which manages the sum of live wind functions for flexible turbulence control."""
    def __init__(self):
        self.start_time = None # for SDK Start time not experimentclock
        self.MAX_SAFETY_LIMIT = 65
        self.phase_offset = 0

    def __call__(self, x_pos, y_pos, time): # for windsuite SDK to call
        if self.start_time is None:
            self.start_time = time

        time -= self.start_time
        result = self._generate_sine_sum(x_pos, y_pos, time) + ControlFeedbackState.mean_velocity_pwm
        return self._clamp(result, 0, self.MAX_SAFETY_LIMIT)

    def add_phase_offset(self, new_phase_offset):
        self.phase_offset += new_phase_offset

    def _generate_sine_sum(self, x_pos, y_pos, time) -> float:
            sine_sum = 0
            for sines in ControlFeedbackState.frequency_band_sines:
                    sine_sum += (sines.amplitude * sin(2 * pi * sines.frequency * time + sines.phase_offset + self.phase_offset))
            return sine_sum

    def _clamp(self, value, min_limit, max_limit):
            return max(min_limit, min(value, max_limit))

class LiveSineWindFunction():
    """Class acts as a wind function for windsuite SDK however the difference is parameters can be adjusted whilst windsuite SDK is utilising the function.
    Has attributes which also log measured amplitude to compare to targetted ones and store the respective controller used"""
    def __init__(self, frequency, rng): # specific seeded rng to have repeatable 'random' phases generated for each experiment
        self.start_time = None
        self.frequency = frequency
        self.amplitude = 0
        self.phase_offset = rng.uniform(0, 2 * np.pi)

        # Controller measurement, target and storage
        self.measured_amplitude = 0
        self.target_amplitude = 0
        self.controller = None

    def update_amplitude(self, new_amplitude):
        self.amplitude = new_amplitude

    def set_controller(self, KP, KI, KD):
        self.controller = PIDController(KP, KI, KD)
