from models.NewProbe import NewProbe
from models.OldProbe import OldProbe
from models.WindController import WindController
from models.DeviceDataManager import DeviceDataManager
from models.ExperimentConfig import ExperimentConfig
from models.LivePlotter import LivePlotter
import models

import time
import threading

# MAIN THREAD OPERATION
class DeviceManager():
    def __init__(self, config: ExperimentConfig):
        # measurement device dict {ID: DeviceType, etc.}
        self.config = config
        self.device_dict = config.measurement_device_dict
        self.windcontroller = WindController(config.wall)
        self._check_device_dict()

        self.registered_devices = []
        self.data_manager = None
        self._generate_device_instances()

        self.start_time = 0
        self.windcontrol_thread = None
        self.writer_thread = None

        self.stop_event = threading.Event()
        
    def check_device_connections(self): # for those devices which have it, windcontroller already does it upon initialisation
        for devices in self.registered_devices:
            if type(devices) == OldProbe:
                devices.connect_to_probe()
            elif type(devices) == NewProbe:
                pass # no connection checker

    def start_devices(self):
        # Windshaper initialisation (Background process)
        self.windcontrol_thread = threading.Thread(target=self.config.profile,args=tuple([self.windcontroller,*self.config.profile_arguments]))
        self.windcontrol_thread.daemon = True
        # Data Writer initialisation (Background process)
        self.writer_thread = threading.Thread(target=self.data_manager.update_dataset_thread)
        self.writer_thread.daemon = True 

        # Windcontrol Start
        self.windcontrol_thread.start()

        # Measurement Device Start (Main Thread Process)
        self.start_time = time.perf_counter()
        for devices in self.registered_devices:
            devices.start(self.start_time)
        self.data_manager.set_metadata()

        # Writer Start
        self.writer_thread.start()

        # Live plotter initialisation (Background multiprocess (not thread))
        self._set_live_plotting_instances()

        # Reading Loop
        self.run_devices()

    def run_devices(self):
        try:
            while not self.stop_event.is_set():
                for devices in self.registered_devices:
                    if type(devices) == OldProbe:
                        if devices.probe_error.is_set() or devices.stop_event.is_set():
                            break
                        devices.transceiver.reading_routine()
                    elif type(devices) == NewProbe:
                        pass # No special process required during loop for new probe.

                if not self.windcontrol_thread.is_alive():
                    print("[WINDSHAPER] WindShaper thread completed its profile. Terminating script...")
                    self.stop_event.set()

        except KeyboardInterrupt:
            print("Forcing Shutdown...")

        finally:
            if not self.stop_event.is_set():
                self.stop_event.set()
            self.stop_devices()

    def stop_devices(self):
        self.windcontroller.stop_windshaper() # stops fans in event of emergency stop trigger
        for devices in self.registered_devices:
            devices.stop()
        self.writer_thread.join(timeout=1)
        self.windcontrol_thread.join(timeout=1)
        self.windcontroller.turnoff_windshaper()

    def save_data(self):
        self.data_manager.save_data()

    def _check_device_dict(self) -> None:
        for ids, devices in self.device_dict.items():
            if devices not in (models.OldProbe.OldProbe, models.NewProbe.NewProbe):
                raise TypeError(f"[DEVICEMANAGER] Invalid Device detected: {devices}, ID: {ids}")

    def _generate_device_instances(self) -> None:
        for ids, devices in self.device_dict.items():
            new_device = devices(self.windcontroller, ids)
            self.registered_devices.append(new_device)
        self.data_manager = DeviceDataManager(self.registered_devices, self.config)

    def _set_live_plotting_instances(self) -> None:
        # CURRENTLY LIVE PLOTTER ONLY SUPPORTS ONE DEVICE
        if self.config.live_probe_data:
            probe_plot = True 
        if self.config.live_windshaper_data:
            wind_plot = True

        if wind_plot or probe_plot:
            single_device = self.registered_devices[0]
            single_device.plotter = LivePlotter(single_device.ID ,probe_plot, wind_plot, (self.windcontroller.fan_rows,self.windcontroller.fan_columns))




    