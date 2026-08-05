import time

class ExperimentClock():
    def __init__(self):
        self.start_time = 0
        self.timer_start_time = 0
        self.calibration_timer_start_time = 0
        
    def start_clock(self):
        self.start_time = time.perf_counter()

    def start_timer(self):
        self.timer_start_time = time.perf_counter()

    def start_calibration_timer(self):
        self.calibration_timer_start_time = time.perf_counter()

    @property
    def time_elapsed(self):
        return time.perf_counter() - self.start_time

    @property
    def timer_time_elapsed(self):
        return time.perf_counter() - self.timer_start_time

    @property
    def calibration_timer_time_elapsed(self):
        return time.perf_counter() - self.calibration_timer_start_time

