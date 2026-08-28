from abc import ABC, abstractmethod
from models.experiment.ExperimentConfig import ExperimentConfig

class BaseCalibration(ABC):
    # REQUIRED PROPERTIES OF A CALIBRATOR
    config: ExperimentConfig
    calibration_meta_data_label: str
    x_gain: float
    y_gain: float
    z_gain: float
    x_intercept: float
    y_intercept: float
    z_intercept: float

    # REQUIRED METHODS
    @abstractmethod
    def __init__(self, config: ExperimentConfig):
        """All calibrators must have a configuration implementation"""
        pass

    @abstractmethod
    def run(self):
        """All calibrators must have a run initialisation, this must run the calibration and calculate the gains/intercepts, and store them in the required properties above."""
        pass