import threading
import time
import numpy as np
import logging

from models.wind.WindController import WindController
from models.experiment.ExperimentClock import ExperimentClock
from models.data.ProbeFeedbackState import ProbeFeedbackState
from models.windprobe_api import ProbeRawData, Vec3, ProbeConversionStatus

logger = logging.getLogger(__name__)

class SimProbe:
    """Class which simulates identical behaviour to a standard OldProbe with artificial scaled velocity and scaled turbulence.
    Useful for debugging without an actual probe (I can totally relate to this). Modelled after a small time lag after RPM.
    This probe operates an additional thread dedicated to simulating live data alongside currently existing plotting multiprocess and error threads.
    NOTE: Mathematics behind turbulence is taken from AI."""
    def __init__(self, windshaper_instance: WindController, ID, clock: ExperimentClock, feedback_state: bool = False) -> None:
        """Initialisation function which acts identically to OldProbe. Additional tuning parameters for simulation aswell."""
        self.current_buffer_data = []
        self.probe_ready = threading.Event()
        self.probe_error = threading.Event()
        self.stop_event = threading.Event()
        self.buffer_lock = threading.Lock()

        self.windshaper = windshaper_instance.windwrapper
        self.clock = clock
        self.ID = ID

        self.plotter = None
        self.feedback_state = feedback_state

        self.failed_connect_notif = False

        self.plot_fq_limiter = 0

        # simulation 
        self.velocity = 0.0
        self.turbulence = 0.0
        self.last_time = 0

        # Tunable parameters
        self.response_time = 0.3        # seconds from rpm response
        self.rpm_gain = 0.00123             # m/s per RPM

    def connect_to_probe(self) -> bool:
        self.probe_ready.set()
        logging.info("Simulated Probe Connected.")
        return True

    def start(self) -> bool:
        """Function which triggers the simulation thread and error thread for the simulation."""
        if not self.probe_ready.is_set():
            logging.info("Simulated Probe Failed to start.")
            return False

        self.sim_thread = threading.Thread(target=self._simulation_loop, daemon=True,)
        self.sim_thread.start()

        self.error_thread = threading.Thread(target=self._monitor_errors,daemon=True,)
        self.error_thread.start()
        return True

    def stop(self) -> None:
        """Function which stops the error thread, triggers stop event and stops simulation thread."""
        self.stop_event.set()

        if hasattr(self, "sim_thread"):
            self.sim_thread.join()

        if hasattr(self, "error_thread"):
            self.error_thread.join()

        if self.plotter:
            self.plotter.close()

    def _simulation_loop(self):
        """Function which simulates velocity and turbulence based on live windshaper statistics."""
        while not self.stop_event.is_set():
            now = self.clock.time_elapsed
            dt = now - self.last_time
            self.last_time = now

            rpm = self.windshaper.array_state.current_avg_upstream_rpm

            target_velocity = rpm * self.rpm_gain

            self.velocity += (dt / self.response_time) * (target_velocity - self.velocity)

            TI = max((4.2 - 0.00028 * rpm) / 100, 0.005)

            sigma = abs(self.velocity) * TI

            alpha = np.exp(-dt / 0.02)

            self.turbulence = (alpha * self.turbulence + np.sqrt(1 - alpha**2) * np.random.normal(0, sigma))

            vel = self.velocity + self.turbulence

            # Cloned representation of incoming ProbeRawData which would otherwise be produced by the old windprobe_API. 
            # This allows the callback function to behave identically to other probes.
            raw = ProbeRawData(
                windspeed_vels_mps=Vec3(
                    x=np.random.normal(0, 0.01),
                    y=np.random.normal(0, 0.01),
                    z=vel,
                ),
                static_pressure_pascal=0,
                temperature_celcius=0,
                atmospheric_pressure_hpascal=0,
                timestamp_s=now,
                crc_ok=True,
                status_byte=ProbeConversionStatus(0x00),
            )

            self._on_new_probe_data(raw)

    def _on_new_probe_data(self, raw_probe_data: ProbeRawData) -> None:
        """Identical to OldProbe Wind API feedback function. """

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

    def _monitor_errors(self):
        """Monitoring error function thread"""
        while not self.stop_event.is_set():

            if self.probe_error.is_set():
                logger.error("Error detected.")
                self.stop_event.set()
                break

            time.sleep(0.01)