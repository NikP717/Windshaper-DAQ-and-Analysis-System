from dataclasses import dataclass
from typing import ClassVar

@dataclass
class ProbeFeedbackState:
    """Feedback Class which is used in closed loop control referencing within files under models.controllers.
    NOTE: Only one instance of this class exists across the whole repository when code is running. """
    windspeed_x: ClassVar[float] = 0
    windspeed_y: ClassVar[float] = 0
    windspeed_z: ClassVar[float] = 0