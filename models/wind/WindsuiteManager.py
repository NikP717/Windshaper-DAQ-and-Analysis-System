from windsuite_sdk import WindsuiteSDK, ModuleInfo
from dotenv import load_dotenv
import os

from models.wind.WindState import FanState, ModuleState, ArrayState
from models.wind.FanSelection import FanSelection
from itertools import zip_longest

class WindsuiteManager():
    def __init__(self, fan_wall_selection) -> None:
        self.sdk_instance = None
        self.fan_controller = None

        self.fan_wall_selection = fan_wall_selection

        # callback information
        self.array_state = ArrayState(modules=None)

        # Initialisation sequence
        self.start_windshaper()
        self.layouts = self.sdk_instance.layouts.get_available_layouts()
        self.set_wall_selection(self.fan_wall_selection)

        print(f"[WINDCONTROL] Available Number Selection Layouts:")
        output = []
        for index, item in enumerate(self.layouts.names, start=1):
            output.append(f"[{index}]: {item}")
        print(output)

        # Change all module info globally
        ArrayState.module_rows = self.sdk_instance.current_layout.nb_rows
        ArrayState.module_columns = self.sdk_instance.current_layout.nb_columns

        # Windshaper Off Flag
        self.stop_status = False

        # Active Command Storage before running
        self.pwm_commands = []
        self.functions = []
        
    def start_windshaper(self) -> WindsuiteSDK:
        load_dotenv()
        SERVER_IP_ADDRESS = os.getenv("SERVER_IP_ADDRESS", default="192.168.88.40")
        base_url = f"http://{SERVER_IP_ADDRESS}"
        print(f"[WINDCONTROL] Connecting to WindSuite server at {base_url}")

        try:
            sdk = WindsuiteSDK(base_url=base_url)
        except RuntimeError:
            raise RuntimeError("[WINDCONTROL] Connection with Windshaper cannot be detected, check wiring.")
        
        sdk.register_module_update_callback(callback=self._on_module_update)
        sdk.start_communication()
        self.sdk_instance = sdk
        self.fan_controller = sdk.fan_controller
        self.sdk_instance.set_psu(state=True)

    def stop_windshaper(self) -> None:
        self.pwm_commands.clear()
        self.functions.clear()
        self.fan_controller.set_intensity(0).apply()
        self.stop_status = True
        print("[WINDCONTROL] Fans stopped.")

    def turnoff_windshaper(self) -> None:
        self.sdk_instance.cleanup()
        self.sdk_instance.set_psu(False)
        print("[WINDCONTROL] Shut down.")

    def switch_layout(self, new_layout):
        if new_layout in self.layouts.names:
            self.sdk_instance.layouts.set_layout(new_layout)
        else:
            raise NameError(f"[WINDCONTROL] Layout '{new_layout}' cannot be found, try adding it on WindSuite.")
        
    def set_wall_selection(self, wall_select: int) -> None:
        # wall select uses enumerated list of layouts described in objects description
        int_list = range(1,len(self.layouts.names))
        if wall_select not in int_list:
            raise ValueError(f"Incorrect wall selection integer, available integers: {int_list}")
        self.switch_layout(self.layouts.names[wall_select - 1])
        ArrayState.module_rows = self.sdk_instance.current_layout.nb_rows
        ArrayState.module_columns = self.sdk_instance.current_layout.nb_columns

    def add_instr(self, selection: FanSelection, command, mode_type: str):
        # command int or wind function as per windsuite sdk requirements
        if mode_type == "pwm":
            self.pwm_commands.append([selection,command,'pwm'])
        elif mode_type == "func":
            self.functions.append([selection,command,'func'])
        else:
            raise TypeError(f"Unknown command mode type: {mode_type}")

    def apply_instructions(self):
        for pwm, func in zip_longest(self.pwm_commands,self.functions,fillvalue=None):
            if pwm is not None:
                selection, instr, _ = pwm
                controller = selection.apply(self.fan_controller)
                controller.set_intensity(percent=instr)

                controller = selection.apply(self.fan_controller)
                controller.set_intensity(percent=instr)

            if func is not None:
                selection_func, instr_func, _ = func
                controller = selection_func.apply(self.fan_controller)
                controller.set_intensity_function(instr_func)
            
                controller = selection_func.apply(self.fan_controller)
                controller.set_intensity_function(instr_func)

        controller.apply()
        self.pwm_commands.clear()

    # def _apply_windfunction(self,windfunction,duration):
    #     try:
    #         self.windshaper.set_psu(state=True)
    #         self.stop_event.wait(timeout=2)
    #         start_time = time.time()

    #         while not self.stop_event.wait(timeout=(1/25)):
    #             time_elapsed = time.time() - start_time
    #             self.windshaper.fan_controller.set_intensity_function(windfunction).apply()
    #             if time_elapsed > duration:
    #                 break
    #     except KeyboardInterrupt:
    #         print("\n[WINDCONTROL] Shutting down...")
    #         self.stop_event.set()
    #     finally:
    #         self.stop_windshaper()


    def _on_module_update(self,data: dict[tuple[int, int], ModuleInfo]) -> None: 
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

