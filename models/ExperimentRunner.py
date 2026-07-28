from models.ExperimentConfig import ExperimentConfig
from models.ExperimentSeriesDataSet import ExperimentSeriesDataSet
from models.WindTracker import WindTracker
from models.DeviceManager import DeviceManager

import threading
import time
import readchar
import inspect

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
        print(f"Wall Selection: {config.wall}, Profile {config.profile.__name__}, Profile Args {config.profile_arguments}")
        print("---")
        if config.manual_meta_data:
            print(f"Manual Meta Data: {config.manual_meta_data}")
        print("---")
        runner = cls(config)
        runner._run()
        

    def _check_configuration(self) -> None:
        # wind control protection
        sig = inspect.signature(self.config.profile)
        # Filter out 'self' to get the actual expected parameters
        expected_params = [param for name, param in sig.parameters.items() if name != 'self']

        if isinstance(self.config.profile_arguments, (tuple, list)):
            provided_count = len(self.config.profile_arguments)
            
            # Count how many arguments are strictly required (no default value)
            required_params = [p for p in expected_params if p.default is inspect.Parameter.empty]
            
            # Error if too few or too many arguments are provided
            if provided_count < len(required_params) or provided_count > len(expected_params):
                raise ValueError(
                    f"[CONFIG ERROR] Incorrect number of arguments for {self.config.profile.__name__}. "
                    f"Expected between {len(required_params)} and {len(expected_params)}. "
                    f"Got: {provided_count} arguments."
                )
        
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

        # Additional pause time for instructed repetitive instances.
        if self.config.pause_time:
            print(f"[EXPERIMENTRUNNER] Pausing for {self.config.pause_time}s as instructed. ")
            time.sleep(self.config.pause_time)
    