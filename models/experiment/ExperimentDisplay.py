import logging

from models.experiment.ExperimentConfig import ExperimentConfig

logger = logging.getLogger(__name__)

def initialise_experiment_logging():
    """Function which initialises logger format across the repository."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s.%(funcName)s() | %(message)s",
        datefmt="%H:%M:%S",
    )

def display_configuration(config: ExperimentConfig):
    """Function which displays a new experiment configuration being ran in the command prompt."""
    print("\n" + "=" * 60)
    print("NEW CONFIGURATION".center(60))
    print("=" * 60)

    logger.info("Running new configuration...")

    print("\nInput Data")
    print("-" * 60)
    print(f"{'Distance from wall':<20}: {config.distance_from_wall}")
    print(f"{'Probe position':<20}: {config.probe_position}")
    print(f"{'Repeat':<20}: {config.repeat}")

    print("\nConfiguration")
    print("-" * 60)
    print(f"{'Wall':<20}: {config.wall}")
    print(f"{'Profile':<20}: {config.profile.name}")

    if config.manual_meta_data:
        print("\nManual Metadata")
        print("-" * 60)
        for key, value in config.manual_meta_data.items():
            print(f"{key:<20}: {value}")
    print("=" * 60 + "\n")