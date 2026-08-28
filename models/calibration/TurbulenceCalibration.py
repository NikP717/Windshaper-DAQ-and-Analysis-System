from models.wind.FanSelection import FanSelection
from models.wind.WindProfileBuilder import ControlMode
from models.experiment.ExperimentConfig import ExperimentConfig
from models.wind.WindProfileBuilder import WindProfileBuilder, WindProfile, ControlMode, FanInstruction, FanCommand
from models.data.WindDataset import WindDataset
from models.calibration.BaseCalibration import BaseCalibration

from pathlib import Path
import numpy as np
from scipy import stats
from math import sin, pi, sqrt


class TurbulenceCalibration(BaseCalibration):
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.x_gain = 0
        self.y_gain = 0
        self.z_gain = 0
        self.x_intercept = 0
        self.y_intercept = 0
        self.z_intercept = 0

        self.calibration_meta_data_label = "turbulence_cal"

        self.base_pwm_sequence = [10,15,20,25,30]
        self.time_step = 25

        self.pwm_sequence = self._determine_pwm_sequence() 
        self.duration = (len(self.pwm_sequence) + 1) * self.time_step
        self.time_sequence = list(range(self.time_step, self.duration + self.time_step, self.time_step))

    def run(self) -> None:
        self._run_pwm_series()
        data = self._get_new_winddata()
        v_x_series = data.probe_data['windspeed_x'].to_numpy()
        v_y_series = data.probe_data['windspeed_y'].to_numpy()
        v_z_series = data.probe_data['windspeed_z'].to_numpy()
        time_series = data.probe_data['time_s'].to_numpy()

        ti_x_list = []
        ti_y_list = []
        ti_z_list = []
        # (time_series <= time) & (time_series > self.time_sequence[time_index-1]+3)
        # go through each condition change from calibration to take relevant TI quantities for each condition
        for time_index, time in enumerate(self.time_sequence): 
            try:
                time_window_mask = (time_series > time + 3) & (time_series <= self.time_sequence[time_index+1])  # dont include first 3 second transient between conditions
            except IndexError:
                continue # ends at end of time windows
            vx = v_x_series[time_window_mask]
            vy = v_y_series[time_window_mask]
            vz = v_z_series[time_window_mask]
            ti_x_list.append(np.nanstd(vx)/np.nanmean(vx))
            ti_y_list.append(np.nanstd(vy)/np.nanmean(vy))
            ti_z_list.append(np.nanstd(vz)/np.nanmean(vz))

        pwm_ti_list = []
        for base_pwm, amplitude_pwm in self.pwm_sequence:
            pwm_ti_list.append(amplitude_pwm/(sqrt(2)*base_pwm))
            
        # gains between pwm equivalent turbulence and velocity turbulence
        slopex, interceptx, _, _, _ = stats.linregress(pwm_ti_list, ti_x_list)
        slopey, intercepty, _, _, _ = stats.linregress(pwm_ti_list, ti_y_list)
        slopez, interceptz, _, _, _ = stats.linregress(pwm_ti_list, ti_z_list)

        self.x_gain = slopex
        self.y_gain = slopey
        self.z_gain = slopez

        self.x_intercept = interceptx
        self.y_intercept = intercepty
        self.z_intercept = interceptz

    def _determine_pwm_sequence(self) -> list:
        """Returns a list of amplitudes and base pwms the configuration profile should follow, in a system like so:
        Base_pwms: 10,20 -> [[base, amplitude], ...]
        It ensures each base pwm configures to the amount of pwm steps it can take in amplitude without exceeding 0 PWM"""
        base_pwms = self.base_pwm_sequence
        sequence = []
        for pwm in base_pwms:
            number_steps = (pwm // 5) - 1
            for step in range(1, number_steps+1):
                sequence.append([pwm, step*5])
        return sequence

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

    def _pwm_series_profile(self) -> WindProfile:
        name = "TURBULENCE CALIBRATION SERIES"
        profile=WindProfileBuilder(self.duration)
    
        selection1 = FanSelection(fans=[1,3,5,7,9], parity="even")
        selection11 = FanSelection(fans=[2,4,6,8], parity="odd")
        selection2 = FanSelection(fans=[1,3,5,7,9], parity="odd")
        selection22 = FanSelection(fans=[2,4,6,8], parity="even")

        all_fans = FanSelection()

        frequency = 0.3
        phase_1 = 2 * pi * frequency
        phase_2 = phase_1 - pi

        t0_1 = 0
        t0_2 = 0
    
        def sine_function_1(x_pos: float, y_pos: float, time: float):
            nonlocal t0_1  # windshaper time isnt zeroed internally
            if t0_1 == 0:
                t0_1 = time 

            time -= t0_1 - self.time_step #profile starts at first time step

            condition_index = int((time - self.time_step) // self.time_step)

            if 0 <= condition_index < len(self.pwm_sequence):
                average, amplitude = self.pwm_sequence[condition_index]
                return average + amplitude * sin(phase_1 * time)

            return self.pwm_sequence[-1][0]
    
        def sine_function_2(x_pos: float, y_pos: float, time: float):
            nonlocal t0_2  # windshaper time isnt zeroed internally
            if t0_2 == 0:
                t0_2 = time 
        
            time -= t0_2 - self.time_step #profile starts at first time step 

            condition_index = int((time - self.time_step) // self.time_step)

            if 0 <= condition_index < len(self.pwm_sequence):
                average, amplitude = self.pwm_sequence[condition_index]
                return average + amplitude * sin(phase_2 * time)

            return self.pwm_sequence[-1][0]


        profile.at_time(0,
                        FanCommand(all_fans, FanInstruction(control_mode=ControlMode.PWM, pwm=10)))
        profile.at_time(self.time_step,
                        FanCommand(selection1, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_function_1)),
                        FanCommand(selection11, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_function_1)),
                        FanCommand(selection2, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_function_2)),
                        FanCommand(selection22, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_function_2))
        )

        return profile.build(name)
    
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
        """Only take the closed loop feedback device to be used for this nested experiment for calibration"""
        dict = self.config.measurement_device_dict
        id = self.config.controller_feedback_probe_list[0]
        probe_type = dict[id]

        new_dict = {id: probe_type}
        return new_dict

