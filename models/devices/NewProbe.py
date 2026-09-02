import threading
import logging

from windsuite_sdk import WindProbeData
from models.wind.WindController import WindController
from models.experiment.ExperimentClock import ExperimentClock
from models.data.ProbeFeedbackState import ProbeFeedbackState

logger = logging.getLogger(__name__)

class NewProbe():
    """Class which acts as a wrapper for the python feedback for the WindShape Series A Probe.
    NOTE: This class is currently untested with the actual Series A Probe - to be tested and modified"""

    def __init__(self, windcontroller_instance: WindController, ID, clock: ExperimentClock, feedback_state: bool = False) -> None:
        """Initialises threading events, data buffer locking, plotting instance, and stores the windcontroller.windwrapper instance for PWM/RPM Feedback"""
        self.current_buffer_data = []
        self.probe_ready = threading.Event()
        self.probe_error = threading.Event()
        self.stop_event = threading.Event()
        self.buffer_lock = threading.Lock()
        self.windshaper = windcontroller_instance.windwrapper
        self.plotter = None
        self.plot_fq_limiter = 0
        self.clock = clock
        self.ID = ID
        self.feedback_state = feedback_state

    def _zero_probe(self) -> bool: 
        """Class which uses inbuilt windsuite SDK zeroing."""
        zero_success = self.windshaper.zero_windprobe()
        if zero_success:
            logging.info("Zeroed Successfully and connected.")
            return True
        else:
            logging.error("Zeroing failed, check connection.")
            return False

    def start(self) -> None:
        self._zero_probe()
        self.windshaper.register_windprobe_callback(callback=self._on_new_probe_data)
        
    def stop(self) -> None:
        self.stop_event.set()

        if self.plotter:
            self.plotter.close()

    def _on_new_probe_data(self, raw_probe_data: WindProbeData) -> None:
        """Standard Windsuite SDK Probe data Callback. Also handles buffer locking of DeviceDataManager, live plotting feedback, 
        closed loop control feedback."""
        if self.stop_event.is_set():
            return
        
        vel = raw_probe_data.wind_velocity_mps_probe_ref
        time_elapsed = self.clock.time_elapsed
        windshape_parameters = self.windshaper.array_state
        
        row =  [
                time_elapsed,
                vel.x,
                vel.y,
                vel.z,
                raw_probe_data.static_pressure_pascal,
                raw_probe_data.temperature_celcius,
                raw_probe_data.atmospheric_pressure_hpascal,
                *windshape_parameters.array_probe_snapshot_upstream,
                *windshape_parameters.array_probe_snapshot_downstream
            ]

        # ensures plotting is updated at a lower frequency to reduce memory load on multiprocess and maintain 200Hz aquiscition.
        # honestly not sure if needed but just safer than sorry
        self.plot_fq_limiter += 1
        if self.plotter and self.plot_fq_limiter % 4 == 0:
            self.plotter.push(row)
            self.plot_fq_limiter = 0

        if self.feedback_state:
            ProbeFeedbackState.windspeed_x = vel.x
            ProbeFeedbackState.windspeed_y = vel.y
            ProbeFeedbackState.windspeed_z = vel.z
        
        with self.buffer_lock:
            self.current_buffer_data.append(row)
    