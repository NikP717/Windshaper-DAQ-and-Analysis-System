from dataclasses import dataclass
from typing import Optional

@dataclass
class FanSelection:
    rows: Optional[list[int]] = None
    columns: Optional[list[int]] = None
    fans: Optional[list[int]] = None
    layer: Optional[str] = None
    parity: Optional[str] = None

    def apply(self, fan_controller):
        controller = fan_controller

        if self.rows:
            controller = controller.rows(self.rows)

        if self.columns:
            controller = controller.columns(self.columns)

        if self.layer == "upstream":
            controller = controller.upstream()
        elif self.layer == "downstream":
            controller = controller.downstream()

        if self.fans:
            controller = controller.fans(self.fans)

        if self.parity == "even":
            controller = controller.even_modules()
        elif self.parity == "odd":
            controller = controller.odd_modules()

        return controller