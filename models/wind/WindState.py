import numpy as np
from dataclasses import dataclass
from typing import ClassVar

"""This file contains a series of nested Windshape states, in a similar nature to WindProfiles it starts small and forms a larger class in the end."""

@dataclass
class FanState:
    """Dataclass which represents the state of a single fan from module callback from windsuite SDK."""
    upstream_pwm: float = 0
    upstream_rpm: float = 0
    downstream_pwm: float = 0
    downstream_rpm: float = 0

    target_upstream_pwm: float = 0
    target_downstream_pwm: float = 0

@dataclass
class ModuleState:
    """Dataclass which represents the state of a single module from module callback from windsuite SDK.
    It also contains methods to output a shaped matrix of its fan statuses."""
    row: int
    col: int
    fans: list[FanState]

    def pwm_matrix(self, layer: str="upstream") -> np.ndarray:
        """Function which outputs a 3,3 numpy matrix of the PWM fan states indexed suitably like the SDK."""
        if layer == "upstream":
            values = [fan.upstream_pwm for fan in self.fans]
        else:
            values = [fan.downstream_pwm for fan in self.fans]
        return np.array(values).reshape(3,3)

    def rpm_matrix(self, layer: str="upstream") -> np.ndarray:
        """Function which outputs a 3,3 numpy matrix of the RPM fan states indexed suitably like the SDK."""
        if layer == "upstream":
            values = [fan.upstream_rpm for fan in self.fans]
        else:
            values = [fan.downstream_rpm for fan in self.fans]
        return np.array(values).reshape(3,3)

@dataclass
class ArrayState:
    """Dataclass which represents the entire wind array, consisting of a series of ModuleStates which contain FanStates.
    This dataclass also enables calculation of array statistics, and outputs probe feedback for data logging.
    NOTE: Single instance of this dataclass exists across the entire repository when running."""
    DIST_BETWEEN_FANS: ClassVar[float] = 0.08
    modules: list[ModuleState]
    module_rows: ClassVar[int] = 0
    module_columns: ClassVar[int] = 0

    """No commenting on alot of these functions below because theyre very self explanatory in the name"""

    @property
    def array_fan_rows(self) -> int:
        return self.module_rows * 3

    @property
    def array_fan_columns(self) -> int:
        return self.module_columns * 3

    @property 
    def current_avg_upstream_pwm_instr(self) -> np.ndarray:
        return np.array([fan.target_upstream_pwm for module in self.modules for fan in module.fans]).mean()

    @property
    def current_avg_downstream_pwm_instr(self) -> np.ndarray:
        return np.array([fan.target_downstream_pwm for module in self.modules for fan in module.fans]).mean()

    @property
    def current_avg_upstream_rpm(self) -> np.ndarray:
        return np.array([fan.upstream_rpm for module in self.modules for fan in module.fans]).mean()

    @property
    def current_avg_downstream_rpm(self) -> np.ndarray:
        return np.array([fan.downstream_rpm for module in self.modules for fan in module.fans]).mean()

    @property
    def current_std_upstream_rpm(self) -> np.ndarray:
        return np.array([fan.upstream_rpm for module in self.modules for fan in module.fans]).std()
    
    @property
    def current_std_downstream_rpm(self) -> np.ndarray:
        return np.array([fan.downstream_rpm for module in self.modules for fan in module.fans]).std()

    
    def pwm_matrix(self, layer:str="upstream") -> np.ndarray:
        """Function which returns a suitably shaped matrix of PWM states as if user were looking upstream at the windshaper.
        Where the matrix shape represents the true fan wall shape with each fan state being in its appropriate position.
        This is used for live plotting feedback."""

        matrix = np.zeros(
            (self.array_fan_rows, self.array_fan_columns)
        )

        for module in self.modules:
            r = (module.row - 1) * 3
            c = (module.col - 1) * 3

            matrix[r:r+3, c:c+3] = module.pwm_matrix(layer)

        return matrix


    def rpm_matrix(self, layer:str="upstream") -> np.ndarray:
        """Function which returns a suitably shaped matrix of RPM states as if user were looking upstream at the windshaper.
        Where the matrix shape represents the true fan wall shape with each fan state being in its appropriate position.
        This is used for live plotting feedback."""

        matrix = np.zeros(
            (self.array_fan_rows, self.array_fan_columns)
        )

        for module in self.modules:
            r = (module.row - 1) * 3
            c = (module.col - 1) * 3

            matrix[r:r+3, c:c+3] = module.rpm_matrix(layer)
        return matrix

    """Functions below act as properties probes draw from to deliver windshape feedback into datasets and live plotting."""

    @property
    def array_probe_snapshot_upstream(self) -> list:
        return [self.current_avg_upstream_pwm_instr,self.current_avg_upstream_rpm,self.current_std_upstream_rpm,self.rpm_matrix(layer="upstream")]

    @property
    def array_probe_snapshot_downstream(self) -> list:
        return [self.current_avg_downstream_pwm_instr,self.current_avg_downstream_rpm,self.current_std_downstream_rpm,self.rpm_matrix(layer="downstream")]
