from dataclasses import dataclass
from models.wind.FanSelection import FanSelection

@dataclass
class FanCommand:
    selection: FanSelection
    mode_type: str # 'func' or 'pwm'
    instruction: object # either pwm or wind function definition

@dataclass
class ProfileStep:
    time: float
    commands: list[FanCommand]

@dataclass
class WindProfile:
    name: str
    duration: float
    steps: list[ProfileStep]


class WindProfileBuilder:
    def __init__(self,duration):
        self.steps = []
        self.duration = duration

    def at_time(self, time, *commands):
        self.steps.append(
            ProfileStep(
                time=time,
                commands=list(commands)
            )
        )
        return self

    def build(self,name):
        return WindProfile(
            name = name,
            duration=self.duration,
            steps=self.steps
        )