from models.calibration.BaseCalibration import BaseCalibration
from models.experiment.ExperimentConfig import ExperimentConfig
from models.wind.WindProfileBuilder import Vel

from pathlib import Path
import json
from datetime import datetime
import time

class CalibrationManager():
    def __init__(self, config: ExperimentConfig, calibration_type: type[BaseCalibration]) -> None:
        self.config = config
        self.calibrate_type = calibration_type(self.config)
        self.calibration_data = None

    def determine_calibration(self) -> None:
        print("[CALBIRATION] Velocity input detected, checking existing calibrations...")
        self._check_existing_calibrations()
        if not self.calibration_data:
            print("[CALBIRATION] No calibration exists for this configuration (using probe_pos, wall, distance_from_wall), starting calibration sequence.")
            time.sleep(2)
            self._create_new_calibration()

    def get_feed_pwm(self, target: float, velocity_component: Vel) -> float:
        if velocity_component == Vel.Z:
            gain = self.calibration_data['z_gain']
            intercept = self.calibration_data['z_intercept']
        elif velocity_component == Vel.Y:
            gain = self.calibration_data['y_gain']
            intercept = self.calibration_data['y_intercept']
        elif velocity_component == Vel.X:
            gain = self.calibration_data['x_gain']
            intercept = self.calibration_data['x_intercept']
        else:
            raise ValueError(f"Unsupported velocity component: {velocity_component}")
        return (target - intercept) / gain
        
    def _check_existing_calibrations(self) -> None:
        project_dir = Path(__file__).resolve().parent.parent.parent
        dir = project_dir / "WINDCALDATA"
        for file in dir.iterdir():
            if file.is_file() and file.suffix in ['.json']:
                with open(file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                condition_1 = (loaded_data['wall'] == self.config.wall)
                condition_2 = (loaded_data['distance_from_wall'] == self.config.distance_from_wall)
                condition_3 = (list(loaded_data['probe_position']) == list(self.config.probe_position))
                condition_4 = (loaded_data['label'] == self.calibrate_type.calibration_meta_data_label)

                if condition_1 and condition_2 and condition_3 and condition_4:
                    self._load_calibration(loaded_data)

    def _create_new_calibration(self) -> None:
        self.calibrate_type.run()
        self._save_calibration()

    def _generate_save_metadata(self) -> None:
        metadata = {"wall":self.config.wall,
                    "distance_from_wall":self.config.distance_from_wall,
                    "probe_position":self.config.probe_position}
        return metadata

    def _save_calibration(self) -> None:
        project_dir = Path(__file__).resolve().parent.parent.parent
        dir = project_dir / "WINDCALDATA" 
        dir.mkdir(exist_ok=True)
        data = self._generate_save_metadata()

        data['x_gain'] = self.calibrate_type.x_gain
        data['y_gain'] = self.calibrate_type.y_gain
        data['z_gain'] = self.calibrate_type.z_gain
        data['x_intercept'] = self.calibrate_type.x_intercept
        data['y_intercept'] = self.calibrate_type.y_intercept
        data['z_intercept'] = self.calibrate_type.z_intercept
        data['label'] = self.calibrate_type.calibration_meta_data_label
        self.calibration_data = data
        file_path = dir / f"Calibration_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json"

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

    def _load_calibration(self, data: dict) -> None:
        self.calibration_data = data