from models.wind.WindProfileBuilder import WindProfileBuilder, FanCommand, WindProfile
from models.wind.FanSelection import FanSelection
from models.wind.WindState import ArrayState
from math import sin, pi
import numpy as np

ALL_FANS = FanSelection()
UPSTREAM_FANS = FanSelection(layer="upstream")
DOWNSTREAM_FANS = FanSelection(layer="downstream")


def uniform_flow(duration,pwm):
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

# def alpha_boundary_layer(pwm_max, alpha, duration):
#     rows = ArrayState.module_rows * 3
#     fan_sep = ArrayState.DIST_BETWEEN_FANS
#     z_ref = fan_sep * rows - fan_sep/2
#     z_array = np.linspace(fan_sep/2,z_ref,rows).tolist()
#     z_array_new = []
#     for z in z_array:
#         z_array_new.append([z])
#     z_array = np.array(z_array_new[::-1])
#     row_instr = (pwm_max*(z_array/z_ref)**alpha).tolist()

#     def alpha_bl_function(x_pos: float, y_pos: float, time: float):
#         intensity = 
