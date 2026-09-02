from windsuite_sdk import WindsuiteSDK, ModuleInfo
from dotenv import load_dotenv
import os
import math
import logging

from models.wind.WindState import FanState, ModuleState, ArrayState
from models.wind.FanSelection import FanSelection
from models.wind.WindProfileBuilder import ControlMode, FanInstruction
from models.experiment.ExperimentSafety import ExperimentSafety
from itertools import zip_longest

logger = logging.getLogger(__name__)

class WindsuiteManager():
    """Class which acts as the official wrapper for WindSuite SDK code, referred to as 'windwrapper' in other files commonly.
    Interfaces directly with connection and actuation of the windshaper. This is the lowest level (base) class in WindControl."""
    def __init__(self, fan_wall_selection: int) -> None:
        """Initialises safety limits, array state, windshaper start up sequence and wall selection."""
        self.sdk_instance = None
        self.fan_controller = None
        self.PWM_SAFETY_LIMIT = ExperimentSafety.MAX_PWM

        self.fan_wall_selection = fan_wall_selection

        # callback information
        self.array_state = ArrayState(modules=None)

        # Initialisation sequence
        self.start_windshaper()
        self.layouts = self.sdk_instance.layouts.get_available_layouts()
        self.set_wall_selection(self.fan_wall_selection)

        logger.info("Available Number Selection Layouts:")
        output = []
        for index, item in enumerate(self.layouts.names, start=1):
            output.append(f"[{index}]: {item}")
        logger.info(output)

        # Change all module info globally
        ArrayState.module_rows = self.sdk_instance.current_layout.nb_rows
        ArrayState.module_columns = self.sdk_instance.current_layout.nb_columns

        # Windshaper Off Flag
        self.stop_status = False

        # Active Command Storage before running
        self.pwm_commands = []
        self.functions = []
       
        
    def start_windshaper(self):
        """Function which initialises Windsuite Server connection, module callback communication and activates the PSUs."""
        load_dotenv()
        SERVER_IP_ADDRESS = os.getenv("SERVER_IP_ADDRESS", default="192.168.88.40")
        base_url = f"http://{SERVER_IP_ADDRESS}"
        logger.info(f"Connecting to WindSuite server at {base_url}")

        try:
            sdk = WindsuiteSDK(base_url=base_url)
        except RuntimeError:
            raise RuntimeError("Connection with Windshaper cannot be detected, check wiring.")
        
        sdk.register_module_update_callback(callback=self._on_module_update)
        sdk.start_communication()
        self.sdk_instance = sdk
        self.fan_controller = sdk.fan_controller
        self.sdk_instance.set_psu(state=True)

    def stop_windshaper(self) -> None:
        """Function which clears all fan commands and disables the windshaper."""
        self.pwm_commands.clear()
        self.functions.clear()
        self.fan_controller.set_intensity(0).apply()
        self.stop_status = True
        logger.info("Fans stopped.")

    def turnoff_windshaper(self) -> None:
        """Function which ends SDK communication and disables PSUs."""
        self.sdk_instance.cleanup()
        self.sdk_instance.set_psu(False)
        logger.info("Windsuite SDK shutdown.")

    def switch_layout(self, new_layout) -> None:
        """Function which switches the layout used on the windshaper
        NOTE: No external operation currently uses this, available if needed in future. Only used internally currently."""
        if new_layout in self.layouts.names:
            self.sdk_instance.layouts.set_layout(new_layout)
        else:
            raise NameError(f"[WINDCONTROL] Layout '{new_layout}' cannot be found, try adding it on WindSuite.")
        
    def set_wall_selection(self, wall_select: int) -> None:
        """Function which sets the wall selection inputted by the user, which follows an enumerated list of ones available on Windsuite SDK.
        Upon selection it also updates the global ArrayState dimensions for proper feedback for any sized windshape layout."""
        int_list = range(1,len(self.layouts.names)+1)
        if wall_select not in int_list:
            raise ValueError(f"Incorrect wall selection integer, available integers: {int_list}")
        self.switch_layout(self.layouts.names[wall_select - 1])
        ArrayState.module_rows = self.sdk_instance.current_layout.nb_rows
        ArrayState.module_columns = self.sdk_instance.current_layout.nb_columns

    def add_instr(self, selection: FanSelection, command: FanInstruction) -> None:
        """Function which WindController utilises to add PWM commands and PWM wind functions to Windsuite SDK execution list."""
        if command.control_mode == ControlMode.PWM:
            if command.pwm is not None:
                self.pwm_commands.append([selection,command])
            elif command.pwm_wind_function is not None:
                self.functions.append([selection,command])

    def apply_instructions(self) -> None:  
        """Function which WindController utilises to apply instructions currently stored in WindSuiteManager.
        It takes a zipped list of commands and applies them using WindSuite SDK conventions,
        Upon executing PWM commands, it immediately clears them to not repeat commands.
        Similar to WindController, windfunctions are not cleared and evaluated till the end of windsuite operation."""
        if not self.stop_status:
            for pwm_cmd, func_cmd, in zip_longest(self.pwm_commands,self.functions,fillvalue=None):
                if pwm_cmd is not None:
                    pwm_instr = pwm_cmd[1].pwm

                    if math.isnan(pwm_instr): 
                        self.stop_windshaper()
                        raise ValueError("Invalid PWM")
                    if pwm_instr > self.PWM_SAFETY_LIMIT:
                        self.stop_windshaper()
                        raise ValueError("PWM Exceeds safety limit.")
                    
                    selection, instr = pwm_cmd
                    controller_pwm = instr.pwm
                    controller = selection.apply(self.fan_controller)
                    controller.set_intensity(percent=controller_pwm)
                    controller.apply()

                if func_cmd is not None:
                    selection_func, instr_func = func_cmd
                    controller_func = instr_func.pwm_wind_function
                    controller = selection_func.apply(self.fan_controller)
                    controller.set_intensity_function(controller_func)

                controller.apply()
            self.pwm_commands.clear()
        else:
            self.fan_controller.set_intensity(0).apply()
            
    def _on_module_update(self,data: dict[tuple[int, int], ModuleInfo]) -> None: 
        """Function which acts as callback for the Windshaper fan status and stores it in the ArrayState object for global reference."""
        modules = []
        for (row, col), module_info in data.items():
            fans = []
            for i in range(9):
                fans.append(FanState(
                        upstream_pwm=module_info.current_pwm[0][i],
                        upstream_rpm=module_info.current_rpm[0][i],
                        downstream_pwm=module_info.current_pwm[1][i],
                        downstream_rpm=module_info.current_rpm[1][i],
                        target_upstream_pwm=module_info.target_pwm[0][i],
                        target_downstream_pwm=module_info.target_pwm[1][i]
                    )
                )

            modules.append(ModuleState(row=row, col=col, fans=fans))

        self.array_state.modules = modules

