from models.wind.WindProfileBuilder import WindProfileBuilder, FanCommand, ControlMode, FanInstruction, Vel, SpectralContent
from models.wind.FanSelection import FanSelection
from models.wind.WindState import ArrayState
from math import sin, pi
import numpy as np

"""
The purpose of this script is to allow ConfigureExperiment to refer to these pre-made profiles within configuration, see more in ConfigureExperiment.py.

Key Profile Information
=============================
- A WindProfile contains ProfileSteps which contain any amount of FanCommands.
- ProfileCommands carry a FanSelection and a FanInstruction.

- ProfileSteps are initiated here by profile.at_time(time, FanCommand*) -> Can apply multiple fan commands at one time.
- FanSelection acts as a filter, the more specifiers you use e.g layer, fan_row, parity, etc. the less fans are selected. See models.wind.FanSelection for more.
- Windfunctions must have an x_pos, y_pos, and time field as a requirement of WindSuiteSDK (see sine_flow below for an example) and return an intensity.

- Closed loop and open loop commands cannot be mixed in one profile.

For further details on ProfileSteps, FanCommands, FanInstructions, FanSelections, spectrum selection etc. see models.wind.WindProfileBuilder
"""

ALL_FANS = FanSelection()
UPSTREAM_FANS = FanSelection(layer="upstream")
DOWNSTREAM_FANS = FanSelection(layer="downstream")

"""PWM BASED PROFILES"""

def uniform_flow(pwm, duration):
    name = "uniform_flow"
    profile = WindProfileBuilder(duration)
    profile.at_time(0, 
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.PWM,pwm=pwm)
                               ),
                    )
    return profile.build(name)

def sine_flow(average,frequency,amplitude,duration):
    name = "sine_flow"

    def sine_function(x_pos: float, y_pos: float, time: float):
        intensity = 0 + average + amplitude * sin(2*pi*time*frequency) 
        return intensity
    
    profile = WindProfileBuilder(duration)

    profile.at_time(0,
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.PWM,pwm_wind_function=sine_function)
                               )
                    )
    return profile.build(name)

def step_response(start_pwm, step_pwm, duration_step, duration_before_after_step):
    name = "step_response"
    profile = WindProfileBuilder(duration_step + 2*duration_before_after_step)
    profile.at_time(0,
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.PWM,pwm=start_pwm)
                               )
                    )
    profile.at_time(duration_before_after_step,
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.PWM,pwm=step_pwm)
                               )
                    )
    profile.at_time(duration_before_after_step+duration_step,
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.PWM,pwm=start_pwm)
                               )
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
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.PWM,pwm_wind_function=ramp_func)
                               )
                    )
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
                    FanCommand(selection=checkered_1_up,instruction=FanInstruction(mode_type=ControlMode.PWM,pwm_wind_function=upstream_sine_function_1)),
                    FanCommand(selection=checkered_2_up,instruction=FanInstruction(mode_type=ControlMode.PWM,pwm_wind_function=upstream_sine_function_2)),
                    FanCommand(selection=checkered_1_down,instruction=FanInstruction(mode_type=ControlMode.PWM,pwm_wind_function=downstream_sine_function_1)),
                    FanCommand(selection=checkered_2_down,instruction=FanInstruction(mode_type=ControlMode.PWM,pwm_wind_function=downstream_sine_function_2))
                    )
    return profile.build(name)

def turbulence_response(average_pwm, amplitude_pwm, frequency, duration):
    name = "turbulence_response"
    profile=WindProfileBuilder(duration)

    selection1 = FanSelection(fans=[1,3,5,7,9], parity="even")
    selection11 = FanSelection(fans=[2,4,6,8], parity="odd")
    selection2 = FanSelection(fans=[1,3,5,7,9], parity="odd")
    selection22 = FanSelection(fans=[2,4,6,8], parity="even")

    phase_1 = 2 * pi * frequency
    phase_2 = phase_1 - pi
    t0_1 = 0
    t0_2 = 0

    def sine_function_1(x_pos: float, y_pos: float, time: float):
        nonlocal t0_1  # windshaper time isnt zeroed internally
        if t0_1 == 0:
            t0_1 = time 
    
        time -= t0_1
        intensity = average_pwm + amplitude_pwm * sin(phase_1 * time) 
        return intensity

    def sine_function_2(x_pos: float, y_pos: float, time: float):
        nonlocal t0_2  # windshaper time isnt zeroed internally
        if t0_2 == 0:
            t0_2 = time 
    
        time -= t0_2
        
        intensity = average_pwm + amplitude_pwm * sin(phase_2 * time) 
        return intensity

    profile.at_time(0,
                    FanCommand(selection1, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_function_1)),
                    FanCommand(selection11, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_function_1)),
                    FanCommand(selection2, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_function_2)),
                    FanCommand(selection22, FanInstruction(control_mode=ControlMode.PWM, pwm_wind_function=sine_function_2))
    )

    return profile.build(name)

"""VELOCITY BASED PROFILES"""

def velocity_control_uniform_flow(velocity, duration, TI = None,  spectral_frequency_peaks: None | SpectralContent = None):
    name = "v_control_uniform_flow"
    profile = WindProfileBuilder(duration)
    profile.at_time(0, 
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.VELOCITY,
                                                          velocity=velocity,
                                                          velocity_component=Vel.Z, 
                                                          TI = TI,
                                                          target_spectral_content=spectral_frequency_peaks)
                                )
                    )
    return profile.build(name)

def velocity_control_stress_test():
    name="v_control_debug_test"
    profile = WindProfileBuilder(120)
    profile.at_time(0, 
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.VELOCITY,
                                                          velocity=7,
                                                          velocity_component=Vel.Z, 
                                                          TI = None,
                                                          target_spectral_content=None)
                                )
                    )
    profile.at_time(15, 
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.VELOCITY,
                                                          velocity=10,
                                                          velocity_component=Vel.Z, 
                                                          TI = None,
                                                          target_spectral_content=None)
                                )
                    )
    profile.at_time(30, 
                    FanCommand(selection=ALL_FANS,
                               instruction=FanInstruction(control_mode=ControlMode.VELOCITY,
                                                          velocity=5,
                                                          velocity_component=Vel.Z, 
                                                          TI = None,
                                                          target_spectral_content=None)
                                )
                    )
    return profile.build(name)