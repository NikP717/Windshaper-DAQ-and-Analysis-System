import threading
import time
import math

from models.wind.WindController import WindController
from models.windprobe_api import NucleoProbeTransceiver, ProbeRawData
from models.experiment.ExperimentClock import ExperimentClock

class OldProbe():
    def __init__(self,windshaper_instance: WindController, ID, clock: ExperimentClock):
        self.current_buffer_data = []
        self.probe_ready = threading.Event()
        self.probe_error = threading.Event()
        self.stop_event = threading.Event()
        self.buffer_lock = threading.Lock()
        self.windshaper = windshaper_instance.windwrapper
        self.plotter = None
        self.transceiver = NucleoProbeTransceiver(probe_ready=self.probe_ready,probe_error=self.probe_error,callback_new_probe_data=self._on_new_probe_data)
        self.clock = clock
        self.ID = ID
        self.zeroed_data = [0,0,0,0,0]

        # connection notification manager stored
        self.failed_connect_notif = False
        self.manual_zero_status = True

    def connect_to_probe(self) -> bool:  # BLOCKING FUNCTION, MAIN THREAD WILL NOT RUN UNTIL THIS OCCURS
        # Scan USB for the probe until found
            serial_port = None
            while serial_port is None and not self.stop_event.is_set():
                serial_port = self.transceiver.open_probe_serial()
                if serial_port is None:
                    if not self.failed_connect_notif:
                        print("[WINDPROBE] No connection detected from probe...")
                        self.failed_connect_notif = True
                    time.sleep(1)

            if serial_port is not None:
                self.transceiver.set_serial_port(serial_port)
                self.probe_ready.set()
                print(f"[OLDWINDPROBE] Probe connected.")
                return True
            
            if self.probe_error.is_set():
                print("[OLDWINDPROBE] Probe signalled an error, try reconnecting it.")
                return False

    def _on_new_probe_data(self, raw_probe_data: ProbeRawData) -> None:
        vel = raw_probe_data.windspeed_vels_mps
        time_elapsed = self.clock.time_elapsed
        windshape_parameters = self.windshaper.array_state
        row =  [
                time_elapsed,
                (vel.x - self.zeroed_data[1]),
                (vel.y - self.zeroed_data[2]),
                (vel.z - self.zeroed_data[3]),
                (raw_probe_data.static_pressure_pascal),
                (raw_probe_data.temperature_celcius),
                (raw_probe_data.atmospheric_pressure_hpascal),
                *windshape_parameters.array_probe_snapshot_upstream,
                *windshape_parameters.array_probe_snapshot_downstream
            ]
        
        if not self.manual_zero_status:
            self.zeroed_data = row[:4]
            self.manual_zero_status = True

            i = 0
            for vals in self.zeroed_data:
                new_val = 0 if math.isnan(vals) else vals
                self.zeroed_data[i] = new_val
                i += 1
            
        if self.plotter:
            self.plotter.push(row)
        
        with self.buffer_lock:
            self.current_buffer_data.append(row)

    def _monitor_errors(self):
        while not self.stop_event.is_set():
            if self.probe_error.is_set():
                print("[OLDWINDPROBE] Error detected during measurement.")
                self.stop_event.set()
                break
            time.sleep(0.01) # limit frequency of error checks

    def start(self) -> bool:
        if not self.probe_ready.is_set() or self.probe_error.is_set():
            print("[OLDWINDPROBE] Probe Failed to start, cancelling experiment.")
            return False
        self.error_thread = threading.Thread(target=self._monitor_errors)
        self.error_thread.start()
        self.manual_zero_status = False
        return True
    
    def stop(self):
        self.stop_event.set()
        self.transceiver.serial_port.close()
        if hasattr(self, "error_thread"):
            self.error_thread.join()
        if self.plotter:
            self.plotter.close()
       
