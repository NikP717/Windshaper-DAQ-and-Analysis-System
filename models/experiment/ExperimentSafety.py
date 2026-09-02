from dataclasses import dataclass

@dataclass
class ExperimentSafety():
    """Class which acts as a reference point for limits imposed on wind control and other factors.
    Currently only stores MAX_PWM but can be extended."""
    MAX_PWM: int = 65