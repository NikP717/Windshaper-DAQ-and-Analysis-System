import numpy as np
from windsuite_sdk import WindsuiteSDK, ModuleInfo
import threading
import os
from dotenv import load_dotenv
import time
import random
from math import pi, sin

class WindController():
    def __init__(self,fan_wall):
        self.fan_wall = fan_wall
        self.fan_dist = 0.08 # distance between adjacent fans
        self.windshaper = None
        self.selected_wall_array = None
        # pwm instructions storage - for default meta data convention
        self.pwm_instructions = 0
        self.pwm_upstream_instr = 0
        self.pwm_downstream_instr = 0
        # Windfunction characteristics storage - for default meta data convention
        self.windfunct_fq = 0
        self.windfunct_amplitude = 0
        self.windfunct_average = 0
        # Transient Response characteristics tracking
        self.live_current_pwm = 0  
        self.live_current_rpm = 0 
        self.live_target_pwm = 0
        self.live_current_rpm_variance = 0 
        self.live_current_pwm_variance = 0 
        self.live_pwm_array = [0]
        self.live_rpm_array = [0]
        self.live_snapshot = (self.live_current_pwm,self.live_current_rpm,self.live_target_pwm,self.live_current_pwm_variance,self.live_current_rpm_variance,self.live_pwm_array,self.live_rpm_array)
        # Threading timer
        self.stop_event = threading.Event()
        # Loop Frequency
        self.check_hz = 20
        # Initialisation sequence
        self.start_windshaper()
        self.layouts = self.windshaper.layouts.get_available_layouts()
        # Fan Layout
        self.fan_rows = self.windshaper.current_layout.nb_rows * 3
        self.fan_columns = self.windshaper.current_layout.nb_columns * 3

        self.set_wall_selection(self.fan_wall)

        print(f"[WINDCONTROL] Available Number Selection Layouts:")
        output = []
        for index, item in enumerate(self.layouts.names, start=1):
            output.append(f"[{index}]: {item}")
        print(output)

        self.stop_status = False # flag if windshaper has been stopped prior, prevents double stopping instruction.

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
        self.windshaper = sdk

    def turnoff_windshaper(self) -> None:
        self.windshaper.fan_controller.set_intensity(0).apply()
        self.windshaper.cleanup()
        self.windshaper.set_psu(False)
        print("[WINDCONTROL] Shut down.")

    def stop_windshaper(self) -> None:
        self.stop_event.set()
        self.windshaper.fan_controller.set_intensity(0).apply()
        self.stop_status = True
        print("[WINDCONTROL] Fans stopped.")

    def switch_layout(self, new_layout):
        if new_layout in self.layouts.names:
            self.windshaper.layouts.set_layout(new_layout)
        else:
            raise NameError(f"[WINDCONTROL] Layout '{new_layout}' cannot be found, try adding it on WindSuite.")
        
    def set_wall_selection(self, wall_select: int) -> None:
        # wall select uses enumerated list of layouts described in objects description
        int_list = range(1,len(self.layouts.names))
        if wall_select not in int_list:
            raise ValueError(f"Incorrect wall selection integer, available integers: {int_list}")
        self.switch_layout(self.layouts.names[wall_select - 1])
        self.fan_rows = self.windshaper.current_layout.nb_rows * 3
        self.fan_columns = self.windshaper.current_layout.nb_columns * 3

    def _on_module_update(self,data: dict[tuple[int, int], ModuleInfo]) -> None: 
        current_pwms = []
        current_rpms = []
        target_pwms = []

        downstream_rpm = []
        upstream_rpm = []

        for position, module_info in sorted(data.items()):

            for fan_index in range(len(module_info.target_pwm[0])):
                upstream_rpm.append(module_info.current_rpm[0][fan_index])

            for fan_index in range(len(module_info.target_pwm[1])):
                downstream_rpm.append(module_info.current_rpm[1][fan_index])

            for layer_index in range(len(module_info.target_pwm)):
                for fan_index in range(len(module_info.target_pwm[layer_index])):

                    target_pwms.append(module_info.target_pwm[layer_index][fan_index])
                    current_pwms.append(module_info.current_pwm[layer_index][fan_index])
                    current_rpms.append(module_info.current_rpm[layer_index][fan_index])


        self.live_current_pwm = np.mean(current_pwms)
        self.live_current_pwm_variance = np.std(current_pwms)

        self.live_current_rpm = np.mean(current_rpms)
        self.live_current_rpm_variance = np.std(current_rpms)

        self.live_target_pwm = np.mean(target_pwms)

        self.live_pwm_array = np.array(current_pwms)

        self.live_rpm_array = [np.array(downstream_rpm),np.array(upstream_rpm)]

        self.live_snapshot = (self.live_current_pwm,self.live_current_rpm,self.live_target_pwm,self.live_current_pwm_variance,self.live_current_rpm_variance,self.live_pwm_array,self.live_rpm_array)

    def _assign_pwm(self,pwm, fan_layer=None):
        self.pwm_instructions = pwm
        if fan_layer:
            if fan_layer == "d":
                self.pwm_downstream_instr = pwm
            else:
                self.pwm_upstream_instr = pwm
        else:
            self.pwm_downstream_instr = pwm
            self.pwm_upstream_instr = pwm

    def _run_fans(self, duration, fan_layer, std: int | bool = False, multi_fans = False) -> None:
        def apply_intensity(checkered = False):
            if multi_fans:
                self.windshaper.fan_controller.upstream().set_intensity(percent=self.pwm_upstream_instr)
                self.windshaper.fan_controller.downstream().set_intensity(percent=self.pwm_downstream_instr)
                self.windshaper.fan_controller.apply()
            else:
                if fan_layer == "u":
                    if checkered:
                        self.windshaper.fan_controller.even_modules().fans(fans=[1,3,5,7,9]).upstream().set_intensity(percent=self.pwm_instructions).apply()
                        self.windshaper.fan_controller.odd_modules().fans(fans=[2,4,6,8]).upstream().set_intensity(percent=self.pwm_instructions).apply()
                    else:
                        self.windshaper.fan_controller.upstream().set_intensity(percent=self.pwm_instructions).apply()
                elif fan_layer == "d":
                    if checkered:
                        self.windshaper.fan_controller.even_modules().fans(fans=[1,3,5,7,9]).downstream().set_intensity(percent=self.pwm_instructions).apply()
                        self.windshaper.fan_controller.odd_modules().fans(fans=[2,4,6,8]).downstream().set_intensity(percent=self.pwm_instructions).apply()
                    else:
                        self.windshaper.fan_controller.downstream().set_intensity(percent=self.pwm_instructions).apply()
                else:
                    if checkered:
                        self.windshaper.fan_controller.even_modules().fans(fans=[1,3,5,7,9]).set_intensity(percent=self.pwm_instructions).apply()
                        self.windshaper.fan_controller.odd_modules().fans(fans=[2,4,6,8]).set_intensity(percent=self.pwm_instructions).apply()
                    else:
                        self.windshaper.fan_controller.set_intensity(percent=self.pwm_instructions).apply()

        try:
            self.windshaper.set_psu(state=True)
            self.stop_event.wait(timeout=2)
            apply_intensity()
            start_time = time.time()

            while not self.stop_event.wait(timeout=(1.0 / self.check_hz)):
                time_elapsed = time.time() - start_time
                if time_elapsed > duration:
                    break
                if std:
                    self.pwm_instructions += random.randint(int(-std/2),int(std/2))
                    apply_intensity(checkered=True)

        except KeyboardInterrupt:
            print("\n[WINDCONTROL] Shutting down...")
            self.stop_event.set()
        finally:
            if not self.stop_status:
                self.stop_windshaper()

    def start_uniform_flow(self,pwm,duration,fan_layer=None):
        # fan layer - up stream 'u', down stream'd' - both just dont specify
        self._assign_pwm(pwm,fan_layer)
        self._run_fans(duration,fan_layer)
    
    def start_uniform_flow_multifan(self,pwm_upstream_instr,pwm_downstream_instr,duration):
        fan_layer = None
        self._assign_pwm(pwm_upstream_instr,'u')
        self._assign_pwm(pwm_downstream_instr,'d')
        self._run_fans(duration,fan_layer,multi_fans=True)
    
    def start_checkered_turbulence(self,pwm,std,duration,fan_layer=None): # theres a fan_control funct called set_intensity_function and u can define fans selected (to be changed)
        self._assign_pwm(pwm,fan_layer)
        self._run_fans(duration,fan_layer,std)
    
    def start_boundary_layer(self,pwm_max,alpha,duration,fan_layer=None):
        rows = self.windshaper.current_layout.nb_rows * 3
        z_ref = self.fan_dist * rows - self.fan_dist/2
        z_array = np.linspace(self.fan_dist/2,z_ref,rows).tolist()
        z_array_new = []
        for z in z_array:
            z_array_new.append([z])
        z_array = np.array(z_array_new[::-1])
        self.pwm_instructions = (pwm_max*(z_array/z_ref)**alpha).tolist()
        self._run_fans(duration,fan_layer)

    def _apply_windfunction(self,windfunction,duration):
        try:
            self.windshaper.set_psu(state=True)
            self.stop_event.wait(timeout=2)
            start_time = time.time()

            while not self.stop_event.wait(timeout=(1/25)):
                time_elapsed = time.time() - start_time
                self.windshaper.fan_controller.set_intensity_function(windfunction).apply()
                if time_elapsed > duration:
                    break
        except KeyboardInterrupt:
            print("\n[WINDCONTROL] Shutting down...")
            self.stop_event.set()
        finally:
            self.stop_windshaper()
        
    def start_sine_response(self,average,frequency,amplitude,duration): # average and amplitude in terms of pwm
        self.windfunct_amplitude = amplitude
        self.windfunct_average = average
        self.windfunct_fq = frequency

        def sine_function(x_pos: float, y_pos: float, time: float):
            intensity = average + amplitude * sin(2*pi*time*frequency) 
            return intensity
        
        self._apply_windfunction(sine_function,duration)


    
def main() -> None:
    windshaper = WindController(1)
    windshaper.start_sine_response(30,.5,20,10)
    windshaper.turnoff_windshaper()
    # windshaper.start_checkered_turbulence(30,20,15)
    # windshaper.start_uniform_flow(10,15,'d')
    #windshaper.start_boundary_layer(40,0.75,30)

if __name__ == "__main__":
    main()
