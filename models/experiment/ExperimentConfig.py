import logging
from dataclasses import dataclass
from typing import Optional, Callable

from models.wind.WindProfileBuilder import ControlStatus

logger = logging.getLogger(__name__)

@dataclass
class ExperimentConfig:
    """Class which stores user-facing configuration for running experiments"""
    # Experiment naming parameters and Calibration metadata
    distance_from_wall: float
    probe_position: tuple #(X,Y)
    repeat: int # marks repeat iteration e.g 1 will be labelled as R1, prevents ovewriting repeats of same configuration

    # Profile Management
    wall: int # [1,2,3] -> Configure between 1 wall, 2nd wall (slave) or 3 (both) -> WINDSUITE DEPENDANT
    profile: Callable # Check Profiles for profile functions and required arguments, feel free to add your own

    # Equipment Management
    measurement_device_dict: dict # e.g {"probe_01": OldProbe, "probe_02": SimProbe}, formatting follows: {custom_id: device_type} for unlimited .models.devices probe devices added to this script.

    # Closed Loop Control Management
    controller_feedback_probe_list: Optional[list] = None # Needs to be an existing registered device under measurement_device_dict

    # Experiment Meta Data Override
    manual_meta_data: Optional[dict] = None # e.g {'distance': 10, 'frequency': 5}

    # Optional Tracking prior to measurement
    probe_tracking: Optional[bool] = False # [!] Currently tracking is unreliable and not well tested

    # Optional Pause time between experiments 
    pause_time: Optional[float] = 0

    # Data modification Setting
    time_crop: Optional[tuple] = None #(start_time,end_time) - for cutting off spool up and down of windshaper

    # Optional Live Raw Data Display for Debugging probe or windshaper
    live_probe_data: Optional[bool] = False
    live_windshaper_data: Optional[bool] = False

    def verify_config(self) -> None:
        """Function which checks all required parameters of ExperimentConfig and cross-dependancies (such as closed loop + feedback device)"""
        logger.info("Verifying Experiment Configuration...")
        # device protection
        if self.controller_feedback_probe_list:
            for feedback in self.controller_feedback_probe_list:
                if feedback not in self.measurement_device_dict.keys():
                    raise ValueError(f"Feedback device ID not found in device dict, this device must be an already registered device. ID: {feedback}")
                
        id_list = []
        for id, devices in self.measurement_device_dict.items():
            if id in id_list:
                raise ValueError(f"Cannot have duplicate Device IDs, ID: {id}")
            id_list.append(id)

        if self.profile.control_status == ControlStatus.CLOSED_LOOP:
            if self.controller_feedback_probe_list is None:
                raise ValueError(f"Closed Loop profile requires a controller feedback probe registered (controller_feedback_probe_list in Config)")
        
        # time crop protection
        timeframe = self.time_crop
        if timeframe:
            init_time = timeframe[0] if (timeframe and len(timeframe) > 0) else None
            final_time = timeframe[1] if (timeframe and len(timeframe) > 1) else None
            try:
                init_time = float(init_time)
                final_time = float(final_time)
            except TypeError:
                raise TypeError("Invalid formatting for initial time and final time in time cropping, ensure they are float or integers.")

            # Ensures if one is not included it just includes everything from that respective boundary.
            if not init_time:
                init_time = 0
            if not final_time:
                final_time = float('inf')

            if init_time > final_time:
                raise ValueError(f"Start time is greater than end time for the time crop tuple. Expected to be (init_time, final_time).")
            
            if final_time - init_time < 20:
                logger.warning("Time cropping will be less than 20 seconds, potential for inaccurate statistics.")

        # pause time protection
        try:
            pause_time = float(self.pause_time)
        except TypeError:
            raise TypeError("Pause time must be an integer or float.")
        if pause_time < 0:
            raise ValueError("Cannot have a negative pause time.")