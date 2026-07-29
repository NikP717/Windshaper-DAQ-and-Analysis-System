from models.experiment.ExperimentConfig import ExperimentConfig
from models.experiment.ExperimentRunner import ExperimentRunner
from models.wind.WindController import WindController
from models.devices.OldProbe import OldProbe
from models.devices.NewProbe import NewProbe
import Profiles
import time

"""
Configuration Arguments:
    # Experiment naming parameters [REQUIRED] (will only include repeat in meta data if using manual dict)
    ====================================================================
        distance_from_wall: Optional[float] = 0
        probe_position: Optional[tuple] #(X,Y) = (0,0) -> not associated with tracking just to do with choice
        repeat: int # marks repeat iteration e.g 1 will be labelled as R1, prevents ovewriting repeats of same configuration
    # Profile Management [REQUIRED]
    ====================================================================
        wall: int # [1,2,3] -> Configure between 1 wall, 2nd wall (slave) or 3 (both) - if you modified WindSuite this integer list will be different (in order of list on windsuite)
        profile: str # Check models.WindController for profile functions and required arguments
        profile_arguments: list # Check models.WindController for profile functions and required arguments

    # Equipment Management [REQUIRED]
    ====================================================================
        device_dict: dict # e.g {OldProbe: probe_1, OldProbe: probe_2, NewProbe: probe_3}, formatting follows: {device_type: custom_id} for unlimited .models probe devices added to this script.
    
        
    # Optional experiment modifiers
    ====================================================================
    pause_time: Optional[float] = None -> pause between experiments
    probe_tracking: Optional[bool] = False -> enable probe tracking prior to measurement to position probe appropriately, requires USB connection to tracking camera and **WindVision server connection**

    # Data modification Setting
    ====================================================================
    time_crop: Optional[tuple] = None #(start_time,end_time) - for cutting off spool up and down of windshaper

    # Manual MetaData
    ====================================================================
    [!] Will still always automatically include the repeat marked and probe ID to prevent unintentional duplicates.
    manual_meta_data = Optional[dict] = None   : e.g {'frequency': 10, 'dist': 5}

    Important advice: Metadata must be detailed enough such that only identical configurations are 'repeats' and different configurations can be seperated from one another. 
    For example, you could not have 'P:30, P:30' twice without also specifying 'Distance: 1, Distance: 2' for each case without them being mixed up.

    If no manual meta data is provided the system will provide an automated one based on PWM or wind function frequency depending on scenario.
    You must keep the same meta data format for a given configuration series -> otherwise save experiment series will crash.


"""

#%% LOOP THROUGH CONFIGURATIONS HERE
# start_sine_response(self,average,frequency,amplitude,duration)
#start_boundary_layer(self,pwm_max,alpha,duration,fan_layer=None):
configuration = ExperimentConfig(
            pause_time=0,
            distance_from_wall=0.85,
            probe_position= (0,0),
            repeat=1,
            time_crop = (10,80),
            wall=2,
            profile=Profiles.uniform_flow(90,30),
            manual_meta_data={'test':1,'balls':2},
            measurement_device_dict={'id_test_001':OldProbe},
            probe_tracking = False, # as it stands camera tracking sucks 
            live_probe_data = True,
            live_windshaper_data = True
        )
#  def start_uniform_flow_multifan(self,pwm_upstream_instr,pwm_downstream_instr,duration):
if __name__ == "__main__":
    ExperimentRunner.run_configuration(configuration)
    name = "WONTWORK_TEST"
    ExperimentRunner.save_configuration_series(name)


#%% SAVE EXPERIMENT SERIES OF DATA
