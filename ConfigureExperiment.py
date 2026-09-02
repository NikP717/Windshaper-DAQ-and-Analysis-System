from models.experiment.ExperimentConfig import ExperimentConfig
from models.experiment.ExperimentRunner import ExperimentRunner
from models.devices.OldProbe import OldProbe
from models.devices.NewProbe import NewProbe
from models.devices.SimProbe import SimProbe
from models.wind.WindProfileBuilder import SpectralContent
import Profiles
import time
from models.calibration.TurbulenceCalibration import TurbulenceCalibration

"""
Configuration Arguments:
    # Experiment naming parameters [REQUIRED] (will only include repeat in meta data if using manual dict)
    ====================================================================
        distance_from_wall: Optional[float] = 0 -> reference for calibration and default metadata field
        probe_position: Optional[tuple] #(X,Y) = (0,0) -> reference for calibration and default metadata field (can be anything you desire)
        repeat: int # marks repeat iteration e.g 1 will be labelled as R1, prevents ovewriting repeats of same configuration

    # Profile Management [REQUIRED]
    ====================================================================
        wall: int [1,2,3..] -> configure between an enumerated wall list based on the layout selection available within WindSuite.
        profile: Profile.callable(args*) -> Input the user specified profile from Profiles.py for the configuration to use.

    # Equipment Management [REQUIRED]
    ====================================================================
        device_dict: dict # e.g {'probe_customid_1': OldProbe, 'probe_customid_2': NewProbe, ...}, formatting follows: {custom_id: ProbeType} for unlimited .models probe devices added to this script.
        controller_feedback_probe_list: list[probe_id, ...] its a list but the code doesnt actually support multiple at the minute, must be an ID within device_dict
    
    # Optional experiment modifiers [OPTIONAL]
    ====================================================================
    pause_time: Optional[float] = None -> pause between experiments
    probe_tracking: Optional[bool] = False -> enable probe tracking prior to measurement to position probe appropriately, requires USB connection to tracking camera and **WindVision server connection**

    # Data modification Setting [OPTIONAL]
    ====================================================================
    time_crop: Optional[tuple] = None #(start_time,end_time) - for cutting off spool up and down of windshaper

    # Live Data Display
    ====================================================================
    live_probe_data: Optional[bool] = False -> If user sets to true, one live plotter instance for each probe is displayed of current measurement.
    live_windshaper_data: Optional[bool] = False -> If user sets to true, two live plotter instances for RPM feedback and average/std data is displayed for windshaper.

    # Manual MetaData [OPTIONAL]
    ====================================================================
    [!] Will still always automatically include the repeat marked and probe ID to prevent unintentional duplicates.
    manual_meta_data = Optional[dict] = None   : e.g {'frequency': 10, 'dist': 5}

    Important advice: Metadata must be detailed enough such that only identical configurations are 'repeats' and different configurations can be seperated from one another. 
    For example, you could not have 'P:30, P:30' twice without also specifying 'Distance: 1, Distance: 2' for each case without them being mixed up.

    If no manual meta data is provided the system will provide an automated one based on PWM or wind function frequency depending on scenario.
    You must keep the same meta data format for a given configuration series -> otherwise save experiment series will crash.


"""

#%% LOOP THROUGH CONFIGURATIONS HERE
# velocity_control_uniform_flow(10,5,300)
# configuration = ExperimentConfig(
#             pause_time=0,
#             distance_from_wall=0.85,
#             probe_position= (0,0),
#             repeat=1,
#             time_crop = (60,180), # OPTIONAL
#             wall=2,
#             profile=Profiles.velocity_control_uniform_flow(9,5,190),
#             controller_feedback_probe_list=['probe_1'],
#             manual_meta_data=None,
#             measurement_device_dict={'probe_1':OldProbe},
#             probe_tracking = False, 
#             live_probe_data = True,
#             live_windshaper_data = True
#         )


if __name__ == "__main__":
    # velocity = [5.3, 7.2, 6.3, 8.3]
    # turbulence = [3.5, 4.3, 5.2, 7.1]
    velocity = [8]
    turbulence = [5]
    for v,t in zip(velocity, turbulence):
        configuration = ExperimentConfig(
        pause_time = 10,
        distance_from_wall = 0.85,
        probe_position=(0,0),
        measurement_device_dict={'probe_01': OldProbe},
        controller_feedback_probe_list=['probe_01'],
        repeat=1,
        time_crop=(60,180),
        manual_meta_data={"applied velocity": v, "applied TI": t},
        wall=2,
        profile=Profiles.velocity_control_uniform_flow(v, 180, t),
        live_probe_data=True,
        live_windshaper_data=True
        )
        ExperimentRunner.run_configuration(configuration)
    # frequency = 0.3
    # duration = 70
    # amplitudes = [5,10,15]
    # averages = [30,40,50]
    # for pwm_amp in (amplitudes):
    #     for pwm_base in averages:
    #         configuration = ExperimentConfig(
    #             pause_time = 10,
    #             distance_from_wall = 0.85,
    #             probe_position=(0,0),
    #             measurement_device_dict={'probe_01': OldProbe},
    #             controller_feedback_probe_list=['probe_01'],
    #             repeat=1,
    #             time_crop=(10,60),
    #             manual_meta_data={"amplitude_pwm": pwm_amp, "baseline_pwm": pwm_base},
    #             wall=2,
    #             profile=Profiles.turbulence_response(pwm_base, pwm_amp, frequency, duration),
    #             live_probe_data=True,
    #             live_windshaper_data=True
    #             )
    #         ExperimentRunner.run_configuration(configuration)
    # name = "test_spectral"
    # ExperimentRunner.save_configuration_series(name) # OPTIONAL

# %%
