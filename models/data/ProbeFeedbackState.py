from dataclasses import dataclass
from typing import ClassVar
from models.experiment.ExperimentClock import ExperimentClock

@dataclass
class ProbeFeedbackState:
    windspeed_x: ClassVar[float] = 0
    windspeed_y: ClassVar[float] = 0
    windspeed_z: ClassVar[float] = 0
    last_recorded_time: ClassVar[float] = 0
    dt: ClassVar[float] = 0.005 # assumption originally based off 200hz sensor

    def change_time(self, clock: ExperimentClock) -> None:
        current_time = clock.time_elapsed
        self.dt = current_time - self.last_recorded_time
        self.last_recorded_time = current_time
