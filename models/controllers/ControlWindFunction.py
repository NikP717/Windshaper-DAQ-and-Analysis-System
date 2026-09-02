from math import sin, pi
import numpy as np

from models.wind.WindProfileBuilder import FanInstruction, ControlMode, FanSelection
from models.data.ControlFeedbackState import ControlFeedbackState
from models.controllers.PIDController import PIDController
from models.experiment.ExperimentSafety import ExperimentSafety

class ControlWindFunction():
    """Class which stores the LiveSumWindFunction instances and initialises them for Windsuite SDK to store as a function 
    to evaluate with modifiable parameters live for control."""
    def __init__(self) -> None:
        """Initialises sine sums and applies phase offset for a phase offset turbulence control checkerboard pattern."""
        self.sine_sum_1 = LiveSineSumWindFunction()
        self.sine_sum_2 = LiveSineSumWindFunction()
        self.sine_sum_2.add_phase_offset(-pi)

    def init(self) -> list[list[FanSelection, FanInstruction]]:
        """Post Initialisation (manual) function which creates checkerboard pattern selection 
        for alternated phase sine sums and returns a series of FanCommands ([FanSelection, FanInstruction]) to add the modifiable wind function to the SDK."""
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
    def __init__(self) -> None:
        self.start_time = None # for SDK Start time not experimentclock
        self.MAX_SAFETY_LIMIT = ExperimentSafety.MAX_PWM
        self.phase_offset = 0

    def __call__(self, x_pos: float, y_pos: float, time: float) -> float: # for windsuite SDK to call
        """Class Callable to imitate a function which the SDK uses to allow class parameters to be changed whilst SDK is using it."""
        if self.start_time is None:
            self.start_time = time

        time -= self.start_time
        result = self._generate_sine_sum(x_pos, y_pos, time) + ControlFeedbackState.mean_velocity_pwm
        return self._clamp(result, 0, self.MAX_SAFETY_LIMIT)

    def add_phase_offset(self, new_phase_offset) -> None:
        self.phase_offset += new_phase_offset

    def _generate_sine_sum(self, x_pos, y_pos, time) -> float:
        """Helper function which sums all of the sines stored within ControlFeedbackState and returns a float overall amplitude"""
        sine_sum = 0
        for sines in ControlFeedbackState.frequency_band_sines:
                sine_sum += (sines.amplitude * sin(2 * pi * sines.frequency * time + sines.phase_offset + self.phase_offset))
        return sine_sum

    def _clamp(self, value: float, min_limit: int, max_limit: int) -> float:
        """Helper function which bounds a value between a minima and maxima"""
        return max(min_limit, min(value, max_limit))

class LiveSineWindFunction():
    """Class acts as a wind function for windsuite SDK however the difference is parameters can be adjusted whilst windsuite SDK is utilising the function.
    Has attributes which also log measured amplitude to compare to targetted ones and store the respective controller used"""
    def __init__(self, frequency: float, rng: np.random) -> None: # specific seeded rng to have repeatable 'random' phases generated for each experiment
        self.start_time = None
        self.frequency = frequency
        self.amplitude = 0
        self.phase_offset = rng.uniform(0, 2 * np.pi)

        # Controller measurement, target and storage
        self.target_relative_amplitude = 0
        self.target_absolute_amplitude = 0
        self.controller = None

    def update_amplitude(self, new_amplitude: float) -> None:
        self.amplitude = new_amplitude

    def set_controller(self, KP: float, KI: float, KD: float) -> None:
        self.controller = PIDController(KP, KI, KD)
