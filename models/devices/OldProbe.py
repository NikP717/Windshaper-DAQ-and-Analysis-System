import threading
import time
import logging

from models.wind.WindController import WindController
from models.windprobe_api import NucleoProbeTransceiver, ProbeRawData
from models.experiment.ExperimentClock import ExperimentClock
from models.data.ProbeFeedbackState import ProbeFeedbackState

logger = logging.getLogger(__name__)

class OldProbe():
    """Class which acts as a wrapper for the python feedback for the WindShape Series X Probe.
    NOTE: This class uses the no-longer-distributed Series X Probe, which by the time youre reading this is long redundant so dont use this class."""
    def __init__(self,windshaper_instance: WindController, ID, clock: ExperimentClock, feedback_state: bool = False) -> None:
        """Initialises threading events, data buffer locking, plotting instance, and stores the windcontroller.windwrapper instance for PWM/RPM Feedback"""
        self.current_buffer_data = []
        self.probe_ready = threading.Event()
        self.probe_error = threading.Event()
        self.stop_event = threading.Event()
        self.buffer_lock = threading.Lock()
        self.windshaper = windshaper_instance.windwrapper
        self.plotter = None
        self.plot_fq_limiter = 0
        # Transceiver specific to windprobe_api from before Windsuite SDK days.
        self.transceiver = NucleoProbeTransceiver(probe_ready=self.probe_ready,probe_error=self.probe_error,callback_new_probe_data=self._on_new_probe_data)
        self.clock = clock
        self.ID = ID
        self.tracking_ID = 1

        # connection notification manager stored
        self.failed_connect_notif = False

        # controller feedback 
        self.feedback_state = feedback_state

    def connect_to_probe(self) -> bool:  # BLOCKING FUNCTION, MAIN THREAD WILL NOT RUN UNTIL THIS OCCURS
        """NOTE: BLOCKING FUNCNTION, function which awaits connection to serial port using old probe flags from transceiver."""
        # Scan USB for the probe until found
        serial_port = None
        while serial_port is None and not self.stop_event.is_set():
            serial_port = self.transceiver.open_probe_serial()
            if serial_port is None:
                if not self.failed_connect_notif:
                    logger.warning("No connection detected from probe...")
                    self.failed_connect_notif = True
                time.sleep(1)

        if serial_port is not None:
            self.transceiver.set_serial_port(serial_port)
            self.probe_ready.set()
            logger.info(f"Probe connected.")
            return True
        
        if self.probe_error.is_set():
            logger.error("Probe signalled an error, try reconnecting it.")
            return False

    def _on_new_probe_data(self, raw_probe_data: ProbeRawData) -> None:
        """Old windprobe_API standard callback. Also handles buffer locking of DeviceDataManager, live plotting feedback, 
        closed loop control feedback. """

        if self.stop_event.is_set():
            return
        vel = raw_probe_data.windspeed_vels_mps
        time_elapsed = self.clock.time_elapsed
        windshape_parameters = self.windshaper.array_state

        row =  [
                time_elapsed,
                (vel.x),
                (vel.y),
                (vel.z),
                (raw_probe_data.static_pressure_pascal),
                (raw_probe_data.temperature_celcius),
                (raw_probe_data.atmospheric_pressure_hpascal),
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
            
    def _monitor_errors(self) -> None:
        """Function which uses windprobe_api error flags to check for errors during live data aquiscition on a side thread."""
        while not self.stop_event.is_set():
            if self.probe_error.is_set():
                logger.error("Error detected during measurement.")
                self.stop_event.set()
                break
            time.sleep(0.01) # limit frequency of error checks

    def start(self) -> bool:
        """Function which starts probe error thread, doesnt actually start the probe its callback dependant."""
        if not self.probe_ready.is_set() or self.probe_error.is_set():
            logger.error("[OLDWINDPROBE] Probe Failed to start, cancelling experiment.")
            return False
        self.error_thread = threading.Thread(target=self._monitor_errors)
        self.error_thread.start()
        return True
    
    def stop(self) -> None:
        """Closes transceiver port, closes plot, closes error thread."""
        self.stop_event.set()
        self.transceiver.serial_port.close()
        if hasattr(self, "error_thread"):
            self.error_thread.join()
        if self.plotter:
            self.plotter.close()