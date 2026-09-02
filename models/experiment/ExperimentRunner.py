import threading
import time
import readchar
import logging

from models.experiment.ExperimentConfig import ExperimentConfig
from models.data.ExperimentSeriesDataSet import ExperimentSeriesDataSet
from models.WindTracker import WindTracker
from models.devices.DeviceManager import DeviceManager
import models.experiment.ExperimentDisplay as Display

logger = logging.getLogger(__name__)

class ExperimentRunner:
    """Class which verifies configuration, sequentially triggers DeviceManager Events, controls tracking, and pauses time between experiments."""
    def __init__(self,config: ExperimentConfig) -> None:
        """Init starts: DeviceManager, Experiment Logging, Tracking if selected."""
        Display.initialise_experiment_logging()
        self.config = config
        self.device_manager = DeviceManager(config)

        if self.config.probe_tracking:
            self.tracker = WindTracker(self.device_manager.windcontroller,self.device_manager.registered_devices[0])
            self.tracking_stop_event = threading.Event()
        else:
            self.tracker = False

    @staticmethod
    def save_configuration_series(exp_name: str) -> ExperimentSeriesDataSet:
        """Takes all current /WINDDATA pkl files and compiles them into one dataset witihn /WINDANALYSIS"""
        logger.info("Saving Experiment Series - DO NOT CLOSE.")
        experiment_series_data = ExperimentSeriesDataSet(exp_name)
        experiment_series_data.input_winddata()
        experiment_series_data.save()
        logger.info("Experiment Series Saved.")
        return experiment_series_data

    @classmethod
    def run_configuration(cls, config: ExperimentConfig) -> None:
        """External function which triggers internal run command and configuration display."""
        Display.display_configuration(config)
        runner = cls(config)
        runner._run()

    def _start_tracking_system(self) -> None:
        """Tracking manager function, uses spacebar for zeroing event within WindTracker, BLOCKING FUNCTION,
        does nothing if tracker is not initialised under parent class."""
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
                    logger.info("Tracking ended, experiment starting...")
                    tracking_thread.join(timeout=3)
                    time.sleep(2)  
                time.sleep(.1)

    def _run(self) -> None:
        """Internal running function which verifies experiment configuration, and runs DeviceManager commands and lastly triggers experiment delay."""
        self.config.verify_config()
        self.device_manager.check_device_connections()
        # optional tracking
        self._start_tracking_system()

        self.device_manager.start_devices() # handles running of devices and windshaper too 
        self.device_manager.save_data() # saves data once devices are finished
        self.device_manager.stop_devices()

        # Additional pause time for instructed repetitive instances.
        if self.config.pause_time:
            logger.info(f"Pausing for {self.config.pause_time}s ...")
            time.sleep(self.config.pause_time)
    