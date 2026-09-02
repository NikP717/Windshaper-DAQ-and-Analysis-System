from models.wind.FanSelection import FanSelection
from models.wind.WindProfileBuilder import ControlMode
from models.experiment.ExperimentConfig import ExperimentConfig
from models.wind.WindProfileBuilder import WindProfileBuilder, WindProfile, ControlMode, FanInstruction, FanCommand
from models.data.WindDataset import WindDataset
from models.calibration.BaseCalibration import BaseCalibration
from models.controllers.ControlWindFunction import LiveSineWindFunction

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

        self.base_pwm_sequence = [10,15,20,25]
        self.time_step = 60
        self.time_buffer = 10

        self.pwm_sequence = self._determine_pwm_sequence() 
        print(self.pwm_sequence)
        self.duration = (len(self.pwm_sequence)) * self.time_step
        self.time_sequence = list(range(self.time_step, self.duration + self.time_step, self.time_step))
        print(self.time_sequence)
        print(self.duration)

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
        # go through each condition change from calibration to take relevant TI quantities for each condition
        for time_index, time in enumerate(self.time_sequence): 
            if time_index == len(self.time_sequence) - 1:
                # last window: only lower bound
                time_window_mask = (time_series > time + self.time_buffer)
            else:
                time_window_mask = ((time_series > time + self.time_buffer) & (time_series <= self.time_sequence[time_index+1] - self.time_buffer))

            vx = v_x_series[time_window_mask]
            vy = v_y_series[time_window_mask]
            vz = v_z_series[time_window_mask]
            ti_x_list.append(np.nanstd(vx)/np.nanmean(vx))
            ti_y_list.append(np.nanstd(vy)/np.nanmean(vy))
            ti_z_list.append(np.nanstd(vz)/np.nanmean(vz))

        pwm_ti_list = []
        for base_pwm, amplitude_pwm in self.pwm_sequence:
            pwm_ti_list.append(amplitude_pwm/(sqrt(2)*base_pwm))
        print(pwm_ti_list)
        print(ti_x_list)
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

        sine_eq_1 = LiveSineSumWindFunction()
        sine_eq_2 = LiveSineSumWindFunction()
        sine_eq_2.add_phase_offset(-np.pi)

        def function_1(x_pos: float, y_pos: float, time: float):
            if sine_eq_1.start_time is None:
                sine_eq_1.start_time = time

            time -= sine_eq_1.start_time

            condition_index = int(time // self.time_step)
            if 0 <= condition_index < len(self.pwm_sequence):
                average, amplitude = self.pwm_sequence[condition_index]
                print(f"AVG: {average}, AMP: {amplitude}")
                sine_eq_1.mean_velocity_pwm = average
                individual_sine_amplitude = amplitude / np.sqrt(len(sine_eq_1.sine_array))
                for sines in sine_eq_1.sine_array:
                    sines.amplitude = individual_sine_amplitude

                return sine_eq_1(x_pos, y_pos, time)

            else:
                print("fail condition")
                return self.pwm_sequence[0][0]

        def function_2(x_pos: float, y_pos: float, time: float):
            if sine_eq_2.start_time is None:
                sine_eq_2.start_time = time

            time -= sine_eq_2.start_time

            condition_index = int(time// self.time_step)
            
            if 0 <= condition_index < len(self.pwm_sequence):
                average, amplitude = self.pwm_sequence[condition_index]
                sine_eq_2.mean_velocity_pwm = average
                individual_sine_amplitude = amplitude / np.sqrt(len(sine_eq_2.sine_array))
                for sines in sine_eq_2.sine_array:
                    sines.set_amplitude(individual_sine_amplitude)

                return sine_eq_2(x_pos, y_pos, time)

            else:
                return self.pwm_sequence[0][0]

        profile.at_time(0,
                        FanCommand(all_fans, FanInstruction(control_mode=ControlMode.PWM, pwm=10)))
        profile.at_time(self.time_step,
                        FanCommand(selection1, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=function_1)),
                        FanCommand(selection11, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=function_1)),
                        FanCommand(selection2, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=function_2)),
                        FanCommand(selection22, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=function_2))
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

class LiveSineWindFunction():
    """Class acts as a wind function for windsuite SDK however the difference is parameters can be adjusted whilst windsuite SDK is utilising the function.
    Has attributes which also log measured amplitude to compare to targetted ones and store the respective controller used"""
    def __init__(self, frequency): 
        self.start_time = None
        self.frequency = frequency
        self.amplitude = 0
        self.phase_offset = 0

    def set_amplitude(self, new_target):
        self.amplitude = new_target

class LiveSineSumWindFunction():
    """Class which manages the sum of live wind functions for flexible turbulence control."""
    def __init__(self):
        self.start_time = None # for SDK Start time not experimentclock
        self.phase_offset = 0
        self.sine_array = [LiveSineWindFunction(frequency=fq) for fq in np.arange(0.05, 0.65, 0.05)]
        self.mean_velocity_pwm = 0

    def __call__(self, x_pos, y_pos, time): # for windsuite SDK to call
        if self.start_time is None:
            self.start_time = time

        time -= self.start_time
        result = self._generate_sine_sum(x_pos, y_pos, time) + self.mean_velocity_pwm
        return result

    def add_phase_offset(self, new_phase_offset):
        self.phase_offset += new_phase_offset

    def _generate_sine_sum(self, x_pos, y_pos, time) -> float:
        sine_sum = 0
        for sines in self.sine_array:
            sine_sum += (sines.amplitude * sin(2 * pi * sines.frequency * time + sines.phase_offset + self.phase_offset))
        return sine_sum