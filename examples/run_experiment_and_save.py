from models.ExperimentConfig import ExperimentConfig
from models.ExperimentRunner import ExperimentRunner
from models.WindController import WindController

"""
Configuration Arguments (In Order):
    # Optional experiment modifiers

    pause_time: Optional[float] = None -> pause between experiments
    probe_tracking: Optional[bool] = False -> enable probe tracking prior to measurement to position probe appropriately, requires USB connection to tracking camera

    # Experiment naming parameters

    distance_from_wall: float
    probe_position: tuple #(X,Y) -> not associated with tracking just to do with choice
    repeat: int # marks repeat iteration e.g 1 will be labelled as R1, prevents ovewriting repeats of same configuration

    # Data modification Setting

    time_crop: Optional[tuple] = None #(start_time,end_time) - for cutting off spool up and down of windshaper

    # Profile Management

    wall: int # [1,2,3,..] Each int represents a different layout in WindSuite in order, adding your own means you can use other integers too.
    profile: str # Check WindController for profile functions and required arguments
    profile_arguments: list # Check WindController for profile functions and required arguments

"""

configuration = ExperimentConfig(
            pause_time=5,
            distance_from_wall=0.85,
            probe_position= (0,0),
            repeat=1,
            time_crop = (5,35),
            wall=1,
            profile=WindController.start_uniform_flow,
            profile_arguments= (30,40),
            probe_tracking = False,
            live_probe_data = False
        )
ExperimentRunner.run_configuration(configuration)

name = "test_uniformflow_experiment"
ExperimentRunner.save_experiment_series(name)
