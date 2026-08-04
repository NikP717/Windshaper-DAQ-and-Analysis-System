from models.wind.WindProfileBuilder import WindProfileBuilder, FanCommand
from models.wind.FanSelection import FanSelection
from models.wind.WindState import ArrayState
from math import sin, pi
import numpy as np

ALL_FANS = FanSelection()
UPSTREAM_FANS = FanSelection(layer="upstream")
DOWNSTREAM_FANS = FanSelection(layer="downstream")

# MODULE_ROWS = int(ArrayState.array_fan_rows) / 3
# MODULE_COLUMNS = int(ArrayState.array_fan_columns) /3
# FAN_ROWS = ArrayState.array_fan_rows
# FAN_COLUMNS = ArrayState.array_fan_columns

def uniform_flow(pwm, duration):
    name = "uniform_flow"
    profile = WindProfileBuilder(duration)
    profile.at_time(0, 
                    FanCommand(selection=ALL_FANS,mode_type="pwm",instruction=pwm)
                    )
    return profile.build(name)

def sine_flow(average,frequency,amplitude,duration):
    name = "sine_flow"
    def sine_function(x_pos: float, y_pos: float, time: float):
        intensity = average + amplitude * sin(2*pi*time*frequency) 
        return intensity
    
    profile = WindProfileBuilder(duration)
    profile.at_time(0,
                    FanCommand(selection=ALL_FANS,mode_type="func",instruction=sine_function)
                    )
    return profile.build(name)

def step_response(start_pwm, step_pwm, duration_step, duration_before_after_step):
    name = "step_response"
    profile = WindProfileBuilder(duration_step + 2*duration_before_after_step)
    profile.at_time(0,
                    FanCommand(selection=ALL_FANS,mode_type="pwm",instruction=start_pwm)
                    )
    profile.at_time(duration_before_after_step,
                    FanCommand(selection=ALL_FANS,mode_type="pwm",instruction=step_pwm)
                    )
    profile.at_time(duration_before_after_step+duration_step,
                FanCommand(selection=ALL_FANS,mode_type="pwm",instruction=start_pwm)
                )
    return profile.build(name)

def ramp_response(start_pwm, end_pwm, pwm_rate, duration_peak_ramp, duration_before_after_ramp):
    name = "ramp_response"

    transient_time = (end_pwm - start_pwm) / pwm_rate
    profile = WindProfileBuilder(duration_peak_ramp + 2*duration_before_after_ramp + 2*transient_time)

    t0 = 0

    def ramp_func(x_pos:float, y_pos: float, time: float):
    
        nonlocal t0  # windshaper time isnt zeroed internally
        if t0 == 0:
            t0 = time 

        time -= t0
        
        t_up_start   = duration_before_after_ramp 
        t_peak_start = t_up_start + transient_time 
        t_down_start = t_peak_start + duration_peak_ramp
        t_end_start  = t_down_start + transient_time

        if time < t_up_start:
            return start_pwm

        elif time < t_peak_start:
            return start_pwm + pwm_rate * (time - t_up_start)

        elif time < t_down_start:
            return end_pwm
        
        elif time < t_end_start:
            return end_pwm - pwm_rate * (time - t_down_start)
        else:
            return start_pwm

    profile.at_time(0,
                FanCommand(selection=ALL_FANS,mode_type="func",instruction=ramp_func)
                )
    return profile.build(name)

def alpha_boundary_layer(alpha, top_pwm, duration):
    name="alpha_bl"
    profile=WindProfileBuilder(duration)
    # TO BE FIXED USING NEW FAN ROWS FEATURE
    def alpha_bl_func(x_pos: float, y_pos: float, time: float):
        rows = ArrayState.module_rows * 3
        y_max = rows * ArrayState.DIST_BETWEEN_FANS
        print(f"{y_pos} position, {y_max} max")
        try:
            intensity = int((1 - y_pos/y_max)**alpha) * top_pwm
        except TypeError: # when it becomes complex because it exceeds ymax
            intensity = alpha * top_pwm
        return intensity

    profile.at_time(0,
                    FanCommand(selection=ALL_FANS,mode_type="func",instruction=alpha_bl_func)
                    )
    pass
    return profile.build(name)

def sine_checkered_array(upstream_sine_amp_1, downstream_sine_amp_1, upstream_sine_amp_2, downstream_sine_amp_2, upstream_sine_fq_1, downstream_sine_fq_1, upstream_sine_fq_2, downstream_sine_fq_2, mean_pwm,duration):
    name="sine_checkered_array"
    profile=WindProfileBuilder(duration)

    checkered_1_up = FanSelection(layer="upstream",parity="even",fans=[1,3,5,7,9])
    checkered_2_up = FanSelection(layer="upstream",parity="odd",fans=[2,4,6,8])
    checkered_1_down = FanSelection(layer="downstream",parity="odd",fans=[1,3,5,7,9])
    checkered_2_down = FanSelection(layer="downstream",parity="even",fans=[2,4,6,8])

    def upstream_sine_function_1(x_pos: float, y_pos: float, time: float):
        intensity = mean_pwm + upstream_sine_amp_1 * sin(2*pi*time*upstream_sine_fq_1) 
        return intensity

    def upstream_sine_function_2(x_pos: float, y_pos: float, time: float):
        intensity = mean_pwm - upstream_sine_amp_2 * sin(2*pi*time*upstream_sine_fq_2) 
        return intensity

    def downstream_sine_function_1(x_pos: float, y_pos: float, time: float):
        intensity = mean_pwm + downstream_sine_amp_1 * sin(2*pi*time*downstream_sine_fq_1) 
        return intensity
    
    def downstream_sine_function_2(x_pos: float, y_pos: float, time: float):
        intensity = mean_pwm - downstream_sine_amp_2 * sin(2*pi*time*downstream_sine_fq_2) 
        return intensity

    profile.at_time(0,
                    FanCommand(selection=checkered_1_up,mode_type="func",instruction=upstream_sine_function_1),
                    FanCommand(selection=checkered_2_up,mode_type="func",instruction=upstream_sine_function_2),
                    FanCommand(selection=checkered_1_down,mode_type="func",instruction=downstream_sine_function_1),
                    FanCommand(selection=checkered_2_down,mode_type="func",instruction=downstream_sine_function_2))
    
    return profile.build(name)

