from dataclasses import dataclass
from models.wind.FanSelection import FanSelection
from enum import Enum
from typing import Optional


class ControlMode(Enum):
    PWM = "pwm"
    FUNCTION = "func"
    VELOCITY = "velocity"
    CLOSED_LOOP = "closed_loop"
    OPEN_LOOP = "open_loop"

@dataclass
class FanCommand:
    selection: FanSelection
    mode_type: str # 'func' or 'pwm' or 'velocity'
    instruction: object # either pwm %, velocity m/s, or wind function definition

@dataclass
class ProfileStep:
    time: float
    commands: list[FanCommand]

@dataclass
class WindProfile:
    name: str
    control: str
    duration: float
    steps: list[ProfileStep]


class WindProfileBuilder:
    def __init__(self,duration):
        self.steps = []
        self.duration = duration
        self.open_loop_status = True

    def at_time(self, time, *commands):
        self.steps.append(
            ProfileStep(
                time=time,
                commands=list(commands)
            )
        )
        for command in commands:
            if command.mode_type == ControlMode.VELOCITY:
                self.open_loop_status = False
                break
        return self

    def build(self,name):
        if self.open_loop_status:
            control_status = ControlMode.OPEN_LOOP
        else:
            control_status = ControlMode.CLOSED_LOOP
        return WindProfile(
            name = name,
            control = control_status,
            duration=self.duration,
            steps=self.steps
        )

# NOTE: ADD THESE FEATURES TO BUILD
#     if ControlMode.PWM in step_command_types and ControlMode.VELOCITY in step_command_types:
#     raise RuntimeError("Cannot have PWM commands and VELOCITY command in one WindProfile.")
# if ControlMode.FUNCTION in step_command_types and ControlMode.VELOCITY in step_command_types:
#     raise RuntimeError("Cannot have FUNCTION commands and VELOCITY command in one WindProfile.")