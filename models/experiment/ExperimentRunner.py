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

    def _start_tracking_system(self) -> None:
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

    def _run(self) -> None:
        self.config.verify_config()
        self.device_manager.check_device_connections()
        # optional tracking
        self._start_tracking_system()

        self.device_manager.start_devices() # handles running of devices and windshaper too 
        self.device_manager.save_data() # saves data once devices are finished
        self.device_manager.stop_devices()

        # Additional pause time for instructed repetitive instances.
        if self.config.pause_time:
            print(f"[EXPERIMENTRUNNER] Pausing for {self.config.pause_time}s as instructed. ")
            time.sleep(self.config.pause_time)
    