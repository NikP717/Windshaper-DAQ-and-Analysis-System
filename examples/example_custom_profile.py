"""All User made profiles should go in Profiles.py for consistency
The Following profile shows key features to understand for making a custom user profile"""

from models.wind.WindProfileBuilder import WindProfileBuilder, FanCommand, ControlMode, FanInstruction, Vel
from models.wind.FanSelection import FanSelection
from models.wind.WindState import ArrayState
from math import sin, pi
import numpy as np


ALL_FANS = FanSelection()
UPSTREAM_FANS = FanSelection(layer="upstream")
DOWNSTREAM_FANS = FanSelection(layer="downstream")


def my_custom_profile():
    """Profiles can take as many commands as the user inputs at any specified time step in the duration
    Wind Functions do not end upon starting but user can define function ends within the definition as shown below.
    Only limitation is: Closed Loop Control (Velocity ControlMode) and Open Loop Control (PWM ControlMode) cannot be combined in one profile"""

    name = "my_custom_profile"
    duration = 60
    profile = WindProfileBuilder(duration)
    time_0 = 0

    def sine_function(x_pos: float, y_pos: float, time: float): 
        """Custom Windfunctions REQUIRE x, y, t inputs as per WindShape API and output a PWM
        Feature to note: WindShaper internal timer is not zeroed, must zero yourself if you wish to make time related outputs."""

        # Time zeroing example
        nonlocal time_0  
        if time_0 == 0:
            time_0 = time 
        
        time -= time_0
                
        intensity = 20 + 6 * sin(2*pi*time) 

        if time > 50:
            intensity=0
            
        return intensity

    profile.at_time(0,
                    FanCommand(UPSTREAM_FANS, 
                               FanInstruction(control_mode=ControlMode.PWM,pwm=20)),
                    FanCommand(DOWNSTREAM_FANS,
                               FanInstruction(control_mode=ControlMode.PWM,pwm=40))
                    )
    profile.at_time(30,
                    FanCommand(UPSTREAM_FANS, 
                                FanInstruction(control_mode=ControlMode.PWM,pwm=0)),
                    FanCommand(DOWNSTREAM_FANS,
                               FanInstruction(control_mode=ControlMode.PWM,pwm_wind_function=sine_function))
                    )
    return profile.build(name)