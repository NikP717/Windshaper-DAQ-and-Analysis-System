import numpy as np
from dataclasses import dataclass
from typing import ClassVar

@dataclass
class FanState:
    upstream_pwm: float = 0
    upstream_rpm: float = 0
    downstream_pwm: float = 0
    downstream_rpm: float = 0

    target_upstream_pwm: float = 0
    target_downstream_pwm: float = 0

@dataclass
class ModuleState:
    row: int
    col: int
    fans: list[FanState]

    def pwm_matrix(self, layer: str="upstream") -> np.ndarray:
        if layer == "upstream":
            values = [fan.upstream_pwm for fan in self.fans]
        else:
            values = [fan.downstream_pwm for fan in self.fans]
        return np.array(values).reshape(3,3)

    def rpm_matrix(self, layer: str="upstream") -> np.ndarray:
        if layer == "upstream":
            values = [fan.upstream_rpm for fan in self.fans]
        else:
            values = [fan.downstream_rpm for fan in self.fans]
        return np.array(values).reshape(3,3)

@dataclass
class ArrayState:
    DIST_BETWEEN_FANS: ClassVar[float] = 0.08
    modules: list[ModuleState]
    module_rows: ClassVar[int] = 0
    module_columns: ClassVar[int] = 0

    @property
    def array_fan_rows(self):
        return self.module_rows * 3

    @property
    def array_fan_columns(self):
        return self.module_columns * 3

    @property 
    def current_avg_upstream_pwm_instr(self):
        return np.array([fan.target_upstream_pwm for module in self.modules for fan in module.fans]).mean()

    @property
    def current_avg_downstream_pwm_instr(self):
        return np.array([fan.target_downstream_pwm for module in self.modules for fan in module.fans]).mean()

    @property
    def current_avg_upstream_rpm(self):
        return np.array([fan.upstream_rpm for module in self.modules for fan in module.fans]).mean()

    @property
    def current_avg_downstream_rpm(self):
        return np.array([fan.downstream_rpm for module in self.modules for fan in module.fans]).mean()

    @property
    def current_std_upstream_rpm(self):
        return np.array([fan.upstream_rpm for module in self.modules for fan in module.fans]).std()
    
    @property
    def current_std_downstream_rpm(self):
        return np.array([fan.downstream_rpm for module in self.modules for fan in module.fans]).std()

    
    def pwm_matrix(self, layer:str="upstream") -> None:
        matrix = np.zeros(
            (self.array_fan_rows, self.array_fan_columns)
        )

        for module in self.modules:
            r = (module.row - 1) * 3
            c = (module.col - 1) * 3

            matrix[r:r+3, c:c+3] = module.pwm_matrix(layer)

        return matrix


    def rpm_matrix(self, layer:str="upstream") -> None:
        matrix = np.zeros(
            (self.array_fan_rows, self.array_fan_columns)
        )

        for module in self.modules:
            r = (module.row - 1) * 3
            c = (module.col - 1) * 3

            matrix[r:r+3, c:c+3] = module.rpm_matrix(layer)
        return matrix

    @property
    def array_probe_snapshot_upstream(self):
        return [self.current_avg_upstream_pwm_instr,self.current_avg_upstream_rpm,self.current_std_upstream_rpm,self.rpm_matrix(layer="upstream")]

    @property
    def array_probe_snapshot_downstream(self):
        return [self.current_avg_downstream_pwm_instr,self.current_avg_downstream_rpm,self.current_std_downstream_rpm,self.rpm_matrix(layer="downstream")]
