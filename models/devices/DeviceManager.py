from models.devices.NewProbe import NewProbe
from models.devices.OldProbe import OldProbe
from models.devices.SimProbe import SimProbe
from models.wind.WindController import WindController
from models.data.DeviceDataManager import DeviceDataManager
from models.experiment.ExperimentConfig import ExperimentConfig
from models.LivePlotter import LivePlotter
from models.experiment.ExperimentClock import ExperimentClock
from models.wind.WindState import ArrayState
import models
import threading
import time

# MAIN THREAD OPERATION
class DeviceManager():
    def __init__(self, config: ExperimentConfig) -> None:
        # measurement device dict {ID: DeviceType, etc.}
        # controller probe device list = [] of IDs used for feedback
        self.clock = ExperimentClock()

        self.config = config
        self.device_dict = config.measurement_device_dict
        self.controller_feedback_list = config.controller_feedback_probe_list
        self.windcontroller = WindController(self.config, self.clock)
        self._check_device_dict()

        self.registered_devices = []
        self.data_manager = None
        self._generate_device_instances()

        self.windcontrol_thread = None
        self.writer_thread = None

        self.stop_event = threading.Event()
        
    def check_device_connections(self) -> None: # for those devices which have it, windcontroller already does it upon initialisation
        for devices in self.registered_devices:
            if type(devices) == OldProbe or type(devices) == SimProbe:
                devices.connect_to_probe()
            elif type(devices) == NewProbe:
                pass # no connection checker
    
    def start_devices(self) -> None:
        self.clock.start_clock()
        # Windshaper initialisation (Background process)
        self.windcontrol_thread = threading.Thread(target=self.windcontroller.run_profile,args=())
        self.windcontrol_thread.daemon = True
        # Data Writer initialisation (Background process)
        self.writer_thread = threading.Thread(target=self.data_manager.update_dataset_thread)
        self.writer_thread.daemon = True 

        # Windcontrol Start
        self.windcontrol_thread.start()

        # Measurement Device Start (Main Thread Process)
        for devices in self.registered_devices:
            devices.start()
        self.data_manager.set_metadata()

        # Writer Start
        self.writer_thread.start()

        # Live plotter initialisation (Background multiprocess (not thread))
        self._set_live_plotting_instances()

        # Reading Loop
        self.run_devices()

    def run_devices(self) -> None:
        try:
            while not self.stop_event.is_set():
                # if self.stop_event.wait(0.001):
                #     break
                for devices in self.registered_devices:
                    if type(devices) == OldProbe:
                        if devices.probe_error.is_set() or devices.stop_event.is_set():
                            break
                        devices.transceiver.reading_routine() # only old probe has a transceiver system
                    if type(devices) == SimProbe:
                        time.sleep(0.005) # no internal blocking function, stops from filling CPU

                if not self.windcontrol_thread.is_alive():
                    print("[WINDSHAPER] WindShaper thread completed its profile. Terminating script...")
                    self.stop_event.set()

        except KeyboardInterrupt:
            print("Forcing Shutdown...")
            self.stop_event.set()
            self.windcontroller.stop_control()

        finally:
            if not self.stop_event.is_set():
                self.stop_event.set()

    def stop_devices(self) -> None:
        self.windcontroller.stop_control() # stops fans in event of emergency stop trigger
        for devices in self.registered_devices:
            devices.stop()
        self.data_manager.stop()
        self.writer_thread.join(timeout=1)
        self.windcontrol_thread.join(timeout=1)
        self.windcontroller.end_control()

    def save_data(self) -> None:
        self.data_manager.save_data()

    def _check_device_dict(self) -> None:
        for ids, devices in self.device_dict.items():
            if devices not in (models.devices.OldProbe.OldProbe, models.devices.NewProbe.NewProbe, models.devices.SimProbe.SimProbe):
                raise TypeError(f"[DEVICEMANAGER] Invalid Device detected: {devices}, ID: {ids}")

    def _generate_device_instances(self) -> None:
        for ids, devices in self.device_dict.items():
            
            input_feedback_state = False
            if self.controller_feedback_list is not None:
                if ids in self.controller_feedback_list:
                    input_feedback_state = True

            new_device = devices(self.windcontroller, ids, self.clock, feedback_state=input_feedback_state)
            self.registered_devices.append(new_device)
        self.data_manager = DeviceDataManager(self.windcontroller,self.registered_devices, self.config)

    def _set_live_plotting_instances(self) -> None:
        wind_plot = False
        probe_plot = False
        if self.config.live_probe_data:
            probe_plot = True 
        if self.config.live_windshaper_data:
            wind_plot = True

        if wind_plot or probe_plot:
            i = 0
            for device in self.registered_devices:
                # prevents multiple windshaper callback plots being initiated
                if i != 0:
                    wind_plot_condition = False
                else:
                    wind_plot_condition = wind_plot

                device.plotter = LivePlotter(device.ID , probe_plot, wind_plot_condition, (ArrayState.module_rows*3, ArrayState.module_columns*3))
                i+=1




    