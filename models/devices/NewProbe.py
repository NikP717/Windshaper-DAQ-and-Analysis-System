import threading
from windsuite_sdk import WindProbeData
from models.wind.WindController import WindController
from models.experiment.ExperimentClock import ExperimentClock
from models.data.ProbeFeedbackState import ProbeFeedbackState

class NewProbe():
    def __init__(self,windcontroller_instance: WindController, ID, clock: ExperimentClock, feedback_state: bool = False) -> None:
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
        zero_success = self.windshaper.zero_windprobe()
        if zero_success:
            print("[NEWWINDPROBE] Zeroed Successfully and connected.")
            return True
        else:
            print("[NEWWINDPROBE] [ERROR] Zeroing failed, check connection.")
            return False

    def start(self) -> None:
        self._zero_probe()
        self.windshaper.register_windprobe_callback(callback=self._on_new_probe_data)
        
    def stop(self) -> None:
        self.stop_event.set()

        if self.plotter:
            self.plotter.close()

    def _on_new_probe_data(self, raw_probe_data: WindProbeData) -> None:
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
                
            self.plot_fq_limiter += 1
            if self.plotter and self.plot_fq_limiter % 4 == 0:
                self.plotter.push(row)
                self.plot_fq_limiter = 0

            if self.feedback_state:
                feedback = ProbeFeedbackState()
                ProbeFeedbackState.windspeed_x = vel.x
                ProbeFeedbackState.windspeed_y = vel.y
                ProbeFeedbackState.windspeed_z = vel.z
                feedback.change_time(self.clock)
            
            with self.buffer_lock:
                self.current_buffer_data.append(row)
    