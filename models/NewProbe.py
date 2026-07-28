import os
import threading
import time
from windsuite_sdk import WindProbeData
from models.WindController import WindController

class NewProbe():
    def __init__(self,windshaper_instance: WindController, ID):
        self.current_buffer_data = []
        self.probe_ready = threading.Event()
        self.probe_error = threading.Event()
        self.stop_event = threading.Event()
        self.buffer_lock = threading.Lock()
        self.windshaper = windshaper_instance
        self.plotter = None
        self.start_time = 0
        self.ID = ID

    def _zero_probe(self) -> bool: 
        zero_success = self.windshaper.zero_windprobe()
        if zero_success:
            print("[NEWWINDPROBE] Zeroed Successfully and connected.")
            return True
        else:
            print("[NEWWINDPROBE] [ERROR] Zeroing failed, check connection.")
            return False

    def start(self, start_time) -> None:
        self._zero_probe()
        self.start_time = start_time
        self.windshaper.register_windprobe_callback(callback=self._on_new_probe_data)
        
    def stop(self):
        self.stop_event.set()

        if self.plotter:
            self.plotter.close()

    def _on_new_probe_data(self, raw_probe_data: WindProbeData) -> None:
            vel = raw_probe_data.wind_velocity_mps_probe_ref
            time_elapsed = time.perf_counter() - self.start_time
            windshape_parameters = self.windshaper.live_snapshot
            row =  [
                    time_elapsed,
                    vel.x,
                    vel.y,
                    vel.z,
                    raw_probe_data.static_pressure_pascal,
                    raw_probe_data.temperature_celcius,
                    raw_probe_data.atmospheric_pressure_hpascal,
                    *windshape_parameters #unpacks all winshape live attributes
                ]
                
            if self.plotter:
                self.plotter.push(row)
            
            with self.buffer_lock:
                self.current_buffer_data.append(row)
    