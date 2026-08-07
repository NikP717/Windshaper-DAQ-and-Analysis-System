from dataclasses import dataclass
from models.wind.FanSelection import FanSelection
from enum import Enum
from typing import Optional, Callable


class ControlMode(Enum):
    PWM = "pwm"
    VELOCITY = "velocity"

class Vel(Enum):
    X = "x"
    Y = "y"
    Z = "z"

@dataclass
class FanInstruction:
    control_mode: ControlMode
    pwm: Optional[float] = None
    velocity_component: Optional[Vel] = None
    velocity_wind_function: Optional[Callable] = None
    pwm_wind_function: Optional[Callable] = None
    velocity: Optional[float] = None
    TI: Optional[float] = None
    target_spectral_content: Optional[list] = None

@dataclass
class FanCommand:
    selection: FanSelection
    instruction: FanInstruction

@dataclass
class ProfileStep:
    time: float
    commands: list[FanCommand]

class ControlStatus(Enum):
    CLOSED_LOOP = "closed_loop"
    OPEN_LOOP = "open_loop"

@dataclass
class WindProfile:
    name: str
    control_status: ControlStatus
    duration: float
    steps: list[ProfileStep]

class WindProfileBuilder:
    def __init__(self,duration: float) -> None:
        self.steps = []
        self.duration = duration
        self.open_loop_status = True

    def at_time(self, time: float, *commands) -> None:
        self.steps.append(
            ProfileStep(
                time=time,
                commands=list(commands)
            )
        )
        for command in commands:
            if command.instruction.control_mode == ControlMode.VELOCITY:
                self.open_loop_status = False
                break
        return self

    def _check_build(self) -> None:
        velocity_count = 0
        pwm_count = 0

        for step in self.steps:
            for command in step.commands:
                if command.instruction.control_mode == ControlMode.VELOCITY:
                    velocity_count +=1
                elif command.instruction.control_mode == ControlMode.PWM:
                    pwm_count += 1
        condition_1 = velocity_count !=0
        condition_2 = pwm_count !=0

        if condition_1 and condition_2:
            raise ValueError("Profile Build failed, mixed open loop and closed loop control is incompatible. Cannot be both VELOCITY commands and PWM.")

    def build(self,name: str) -> None:
        self._check_build()
        if self.open_loop_status:
            control_status = ControlStatus.OPEN_LOOP
        else:
            control_status = ControlStatus.CLOSED_LOOP
        return WindProfile(
            name = name,
            control_status = control_status,
            duration=self.duration,
            steps=self.steps
        )
