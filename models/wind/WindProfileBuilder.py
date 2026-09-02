from dataclasses import dataclass
from models.wind.FanSelection import FanSelection
from enum import Enum
from typing import Optional, Callable

"""This file contains a package of classes which increase readability of models.controlllers, models.wind and Profiles.py for user facing customisation.
This file also contains the construction of a user produced wind profile,
 which consists of profile steps, which consists of fan commands which consists of fan instructions and fan selections."""

class ControlMode(Enum):
    """Class which acts as an Enumerate for control modes in WindController."""
    PWM = "pwm"
    VELOCITY = "velocity"

class Vel(Enum):
    """Class which acts as an Enumerate for user selecting which velocity component to control."""
    X = "x"
    Y = "y"
    Z = "z"

@dataclass
class SpectralContent:
    """Frequency amplitude dictionary holder class:
    Dictionary must be: {frequency: amplitude} where amplitude is between 0-1 (relative) and frequency should be under 0.6Hz."""
    frequency_amplitude_dict: dict

@dataclass
class FanInstruction:
    """Dataclass which contains all the instructions a user can apply to wind control."""
    control_mode: ControlMode
    pwm: Optional[float] = None
    velocity_component: Optional[Vel] = None
    pwm_wind_function: Optional[Callable] = None
    velocity: Optional[float] = None
    TI: Optional[float] = None
    target_spectral_content: Optional[SpectralContent] = None

@dataclass
class FanCommand:
    """Dataclass which contains a fan instruction and its respective fan selection."""
    selection: FanSelection
    instruction: FanInstruction

@dataclass
class ProfileStep:
    """Dataclass which contains a series of fan commands at a specified time."""
    time: float
    commands: list[FanCommand]

class ControlStatus(Enum):
    """Enumerate class which is used to classify profiles upon construction for windcontroller to easily identify the nature of the profile."""
    CLOSED_LOOP = "closed_loop"
    OPEN_LOOP = "open_loop"

@dataclass
class WindProfile:
    """Dataclass which contains a series of profile steps, total duration, turbulence control status and a custom name for user labelling."""
    name: str
    control_status: ControlStatus
    duration: float
    steps: list[ProfileStep]
    turbulence_control: bool = False

class WindProfileBuilder:
    """Class which improves user facing construction of custom wind profiles within Profiles.py by enabling 'at_time' instructions, this class then compiles
    user inputs into a WindProfile instance."""
    def __init__(self,duration: float) -> None:
        self.steps = []
        self.duration = duration
        self.open_loop_status = True
        self.turbulence_status = False

    def at_time(self, time: float, *commands) -> None:
        """Function which defines unlimited fan commands at a specific time point in a profile."""
        self.steps.append(
            ProfileStep(
                time=time,
                commands=list(commands)
            )
        )
        # for loop which flips the profile into velocity control mode if a closed loop command is detected.
        for command in commands:
            if command.instruction.control_mode == ControlMode.VELOCITY:
                self.open_loop_status = False
                break
        return self

    def _check_build(self) -> None:
        """Helper function which ensures the profile does not hold mixed closed/open loop commands, and ensures fan commands are within the duration of the profile."""
        velocity_count = 0
        pwm_count = 0

        for step in self.steps:
            # at_time conflict checker
            if step.time > self.duration:
                raise ValueError("Profile Step detected outside profile duration, check 'at_time' commands in Profiles.py ")
            
            for command in step.commands:
                # open loop/closed loop conflict checker.
                if command.instruction.control_mode == ControlMode.VELOCITY:
                    if command.instruction.TI is not None:
                        self.turbulence_status = True
                    velocity_count +=1
                elif command.instruction.control_mode == ControlMode.PWM:
                    pwm_count += 1

        condition_1 = velocity_count !=0
        condition_2 = pwm_count !=0

        if condition_1 and condition_2:
            raise ValueError("Profile Build failed, mixed open loop and closed loop control is incompatible. Cannot be both VELOCITY commands and PWM.")

    def build(self,name: str) -> None:
        """Function which converts WindProfileBuilder instance from user facing Profile.py to a functional WindProfile readable by models.wind code."""
        self._check_build()
        if self.open_loop_status:
            control_status = ControlStatus.OPEN_LOOP
        else:
            control_status = ControlStatus.CLOSED_LOOP
        return WindProfile(
            name = name,
            control_status = control_status,
            turbulence_control = self.turbulence_status,
            duration=self.duration,
            steps=self.steps
        )
