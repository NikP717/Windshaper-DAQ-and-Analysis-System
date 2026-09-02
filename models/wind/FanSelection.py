from dataclasses import dataclass
from typing import Optional

@dataclass
class FanSelection:
    """Dataclass which acts as a wrapper for the WindSuite SDK selection feature and enables an easy user interface for making fan selections.
    In addition to WindSuite SDK features, it also includes fan_rows and fan_columns selection functionality (SDK only has module row/columns as of 01/09/26)."""
    fan_rows: Optional[list[int]] = None
    module_rows: Optional[list[int]] = None
    fans: Optional[list[int]] = None
    fan_columns: Optional[list[int]] = None
    module_columns: Optional[list[int]] = None
    layer: Optional[str] = None
    parity: Optional[str] = None

    def _determine_fan_rows(self) -> tuple[float, float]:
        """Helper function which determines fan row selection by manipulating fan and module row selections existing in the Windsuite SDK.
        (this was made with alot of trial and error!)"""
        fans = []
        module_rows =[]
        for rows in self.fan_rows:
            module_row = (rows-1)//3 + 1
            module_fan_row = rows - (module_row-1)*3
            all_fans = range(1,10)
            index_start = (module_fan_row-1)*3
            index_end = (module_fan_row-1)*3 + 3
            fans_select = all_fans[index_start:index_end]
            fans.extend(fans_select)
            module_rows.append(module_row)
        return fans, module_rows

    def _determine_fan_columns(self) -> None:
        """Helper function which determines fan column selection by manipulating fan and module column selections existing in the Windsuite SDK."""
        fans =[]
        module_cols = []
        for cols in self.fan_columns:
            module_col = (cols-1)//3 + 1
            module_fan_col = cols - (module_col-1)*3
            fans.extend([(module_fan_col)+3*i for i in range(0,3)])
            module_cols.append(module_col)
        return fans, module_cols
        
    def apply(self, fan_controller) -> None:
        """Function which takes the existing fan_controller instance of WindSuiteSDK and applies the user commanded FanSelection as windsuite SDK requires it."""
        controller = fan_controller

        if self.module_rows:
            controller = controller.rows(self.module_rows)

        if self.module_columns:
            controller = controller.columns(self.module_columns)

        # fan row and column intersection logic
        if self.fan_rows or self.fan_columns:
            if self.fan_rows and self.fan_columns:
                row_fans, module_rows = self._determine_fan_rows()
                col_fans, module_cols = self._determine_fan_columns()
                # Ensures fan row and column intersections behave identically to module column/row intersection in the SDK for intuitive usage.
                fans = list(set(row_fans).intersection(col_fans))

                controller = controller.rows(module_rows).columns(module_cols).fans(fans)
                # modules already have inherent intersection I believe
            elif self.fan_rows and not self.fan_columns:
                fans, module_rows = self._determine_fan_rows()
                controller = controller.rows(module_rows).fans(fans)
            elif self.fan_columns and not self.fan_rows:
                fans, module_cols = self._determine_fan_columns()
                controller = controller.columns(module_cols).fans(fans)
                
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
