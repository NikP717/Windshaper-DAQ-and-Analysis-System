from models.experiment.ExperimentConfig import ExperimentConfig
from models.data.ExperimentSeriesDataSet import ExperimentSeriesDataSet
from models.WindTracker import WindTracker
from models.devices.DeviceManager import DeviceManager

import threading
import time
import readchar

class ExperimentRunner:
    def __init__(self,config: ExperimentConfig) -> None:
        self.config = config
        self.device_manager = DeviceManager(config)

        if self.config.probe_tracking:
            self.tracker = WindTracker(self.device_manager.windcontroller,self.device_manager.registered_devices[0])
            self.tracking_stop_event = threading.Event()
        else:
            self.tracker = False

    @staticmethod
    def save_configuration_series(exp_name: str) -> ExperimentSeriesDataSet: # used to push WINDDATA series into WINDANALYSIS single database
        print("[EXPERIMENTRUNNER] Saving Experiment Series, DO NOT CLOSE.")
        experiment_series_data = ExperimentSeriesDataSet(exp_name)
        experiment_series_data.input_winddata()
        experiment_series_data.save()
        print("[EXPERIMENTRUNNER] Saved. ")
        return experiment_series_data

    @classmethod
    def run_configuration(cls, config: ExperimentConfig) -> None:
        print("========================")
        print("[INFO] Running New Configuration")
        print("---")
        print(f"Input Data: \nDistance Wall: {config.distance_from_wall}, Probe pos: {config.probe_position}, Repeat {config.repeat}")
        print(f"Wall Selection: {config.wall}, Profile: {config.profile.name}")
        print("---")
        if config.manual_meta_data:
            print(f"Manual Meta Data: {config.manual_meta_data}")
        print("---")
        runner = cls(config)
        runner._run()
        

    def _check_configuration(self) -> None:
        # time crop protection
        timeframe = self.config.time_crop
        if timeframe:
            init_time = timeframe[0]if (timeframe and len(timeframe) > 0) else None
            final_time = timeframe[1] if (timeframe and len(timeframe) > 1) else None
            try:
                init_time = float(init_time)
                final_time = float(final_time)
            except TypeError:
                raise TypeError("Invalid formatting for initial time and final time in time cropping, ensure they are float or integers.")

            if not init_time:
                init_time = 0
            if not final_time:
                final_time = float('inf')

            if init_time > final_time:
                raise ValueError(f"[CONFIG ERROR] Start time is greater than end time for the time crop tuple. Expected to be (init_time, final_time).")
            
            if final_time - init_time < 20:
                print("[CONFIG WARNING] Time cropping will be less than 20 seconds, potential for inaccuracy when averaging.")

        # pause time protection
        try:
            pause_time = float(self.config.pause_time)
        except TypeError:
            raise TypeError("[CONFIG WARNING] Pause time must be an integer or float.")
        if pause_time < 0:
            raise ValueError("[CONFIG WARNING] Cannot have a negative pause time.")

    def _run(self) -> None:
        self._check_configuration()
        self.device_manager.check_device_connections()

        # optional tracking
        if self.tracker:
            tracking_thread = threading.Thread(target=self.tracker.start)
            tracking_thread.daemon = True

            # main thread key detection upon tracker start
            tracking_thread.start()
            while not self.tracking_stop_event.is_set():
                try:
                    key = readchar.readkey()
                    if key == ' ':
                        self.tracker.reset_position()
                except KeyboardInterrupt:
                    self.tracker.stop_event.set()
                    self.tracking_stop_event.set()
                    
                    print("[INFO] Tracking ended, experiment starting.")
                    tracking_thread.join(timeout=3)
                    time.sleep(2)  
                time.sleep(.1)

        self.device_manager.start_devices() # handles running of devices and windshaper too 
        self.device_manager.save_data() # saves data once devices are finished
        self.device_manager.stop_devices()

        # Additional pause time for instructed repetitive instances.
        if self.config.pause_time:
            print(f"[EXPERIMENTRUNNER] Pausing for {self.config.pause_time}s as instructed. ")
            time.sleep(self.config.pause_time)
    