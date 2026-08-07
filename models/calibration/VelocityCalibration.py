
from models.wind.FanSelection import FanSelection
from models.wind.WindProfileBuilder import ControlMode
from models.experiment.ExperimentConfig import ExperimentConfig
from models.wind.WindProfileBuilder import WindProfileBuilder, FanCommand, ControlMode
from models.data.WindDataset import WindDataset

from pathlib import Path
import numpy as np
from scipy import stats
import math


class VelocityCalibration():
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.vx_gain = 0
        self.vy_gain = 0
        self.vz_gain = 0

        self.pwm_sequence = range(10,66,5)
        self.time_step = 10
        self.duration = len(self.pwm_sequence) * self.time_step + 1
        self.time_sequence = range(self.time_step,self.duration,self.time_step)

    def run(self) -> None:
        self._run_pwm_series()
        data = self._get_new_winddata()
        v_x_series = data.probe_data['windspeed_x'].to_numpy()
        v_y_series = data.probe_data['windspeed_y'].to_numpy()
        v_z_series = data.probe_data['windspeed_z'].to_numpy()
        time_series = data.probe_data['time_s'].to_numpy()
        chunk_duration = 10.0
        buffer_duration = 2 # takes 2 second transient from start
        # each velocity chunk sample is 8 seconds long for each pwm in pwm series
        start_time = time_series[0]
        end_time = time_series[-1]
        vx = []
        vy = []
        vz = []
        pwms = self.pwm_sequence

        current_start = start_time

        for _ in range(len(pwms)):
            current_end = current_start + chunk_duration
            buffer_start = current_start + buffer_duration

            if current_end > end_time:
                current_end = end_time

            mask = (time_series >= buffer_start) & (time_series < current_end)
            
            if np.any(mask):
                vx.append(np.nanmean(v_x_series[mask]))
                vy.append(np.nanmean(v_y_series[mask]))
                vz.append(np.nanmean(v_z_series[mask]))

            current_start = current_end

        slopex, interceptx, _, _, _ = stats.linregress(pwms, vx)
        slopey, intercepty, _, _, _ = stats.linregress(pwms, vy)
        slopez, interceptz, _, _, _ = stats.linregress(pwms, vz)

        if math.isnan(self.vx_gain) or math.isnan(self.vy_gain) or math.isnan(self.vz_gain):
            raise ValueError("Invalid Gain detected, failed callibration.")
        
        self.vx_gain = slopex
        self.vy_gain = slopey
        self.vz_gain = slopez

        if self.vz_gain == 0: # self.vx_gain == 0 or self.vy_gain == 0 or
                    raise ValueError("Zero Gain detected, failed callibration.")

    def _get_new_winddata(self) -> WindDataset:
        project_dir = Path(__file__).resolve().parent.parent.parent
        dir = project_dir / "WINDDATA" 
        type = "*.pkl"
        target_dir = Path(dir)
        files = [f for f in target_dir.glob(type) if f.is_file()]
        newest_file = max(files, key=lambda f: f.stat().st_mtime)
        winddata_obj = WindDataset.load(newest_file)
        newest_file.unlink() # remove temp pkl file for calibration
        return winddata_obj

    def _pwm_series_profile(self) -> None:
        all_fans = FanSelection()
        profile = WindProfileBuilder(max(self.time_sequence)+10)
        times = self.time_sequence
        pwms = self.pwm_sequence
        profile.at_time(0,
                        FanCommand(all_fans,ControlMode.PWM,5)) # initialise fans
        for t,p in zip(times, pwms):
            profile.at_time(t,
                FanCommand(all_fans,ControlMode.PWM,p)
            )
        return profile.build(name="CALIBRATION SERIES")

    def _run_pwm_series(self) -> None:
         # Prevents circular import cycle in the event velocity calibration isnt running 
        from models.experiment.ExperimentConfig import ExperimentConfig
        from models.experiment.ExperimentRunner import ExperimentRunner


        calib_config = ExperimentConfig(
            distance_from_wall=self.config.distance_from_wall,
            probe_position = self.config.probe_position,
            repeat = 1,
            wall = self.config.wall,
            profile=self._pwm_series_profile(),
            measurement_device_dict = self._isolate_single_device_dict(),
            controller_feedback_probe_list= self.config.controller_feedback_probe_list,
            live_probe_data=True,
            live_windshaper_data=True,
            pause_time=5
        )

        ExperimentRunner.run_configuration(calib_config) # nested experiment runner ik insane
        print("[CALIBRATION] Calibration complete.")

    def _isolate_single_device_dict(self) -> None:
        dict = self.config.measurement_device_dict
        id = self.config.controller_feedback_probe_list[0]
        probe_type = dict[id]

        new_dict = {id: probe_type}
        return new_dict