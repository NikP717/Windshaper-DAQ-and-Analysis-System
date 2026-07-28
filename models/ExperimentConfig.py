from dataclasses import dataclass
from typing import Optional


@dataclass
class ExperimentConfig:
    # Experiment naming parameters
    distance_from_wall: float
    probe_position: tuple #(X,Y)
    repeat: int # marks repeat iteration e.g 1 will be labelled as R1, prevents ovewriting repeats of same configuration

    # Profile Management
    wall: int # [1,2,3] -> Configure between 1 wall, 2nd wall (slave) or 3 (both)
    profile: str # Check WindController for profile functions and required arguments
    profile_arguments: list # Check WindController for profile functions and required arguments

    # Equipment Management
    measurement_device_dict: dict # e.g {OldProbe: probe_1, OldProbe: probe_2, NewProbe: probe_3}, formatting follows: {device_type: custom_id} for unlimited .models probe devices added to this script.

    # Experiment Meta Data Override
    manual_meta_data: Optional[dict] = None # e.g {'distance': 10, 'frequency': 5}

    # Optional Tracking prior to measurement
    probe_tracking: Optional[bool] = False # does not support multiple probes atm and only old probe

    # Optional Pause time between experiments 
    pause_time: Optional[float] = None 

    # Data modification Setting
    time_crop: Optional[tuple] = None #(start_time,end_time) - for cutting off spool up and down of windshaper

    # Optional Live Raw Data Display for Debugging probe or windshaper
    live_probe_data: Optional[bool] = False
    live_windshaper_data: Optional[bool] = False