from models.calibration.VelocityCalibration import VelocityCalibration
from models.experiment.ExperimentConfig import ExperimentConfig

from pathlib import Path
import json
from datetime import datetime
import time

class CalibrationManager():
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.calibrate_type = VelocityCalibration(self.config)
        self.calibration_data = None

    def determine_calibration(self) -> None:
        print("[CALBIRATION] Velocity input detected, checking existing calibrations...")
        self._check_existing_calibrations()
        if not self.calibration_data:
            print("[CALBIRATION] No calibration exists for this configuration (using probe_pos, wall, distance_from_wall), starting calibration sequence.")
            time.sleep(2)
            self._create_new_calibration()

    def get_feed_pwm(self, target: float, velocity_component: str) -> float:
        if velocity_component == "vz":
            return target / self.calibration_data['vz_gain']
        if velocity_component == "vy":
            return target / self.calibration_data['vy_gain']
        if velocity_component == "vx":
            return target / self.calibration_data['vx_gain']
        
    def _check_existing_calibrations(self) -> None:
        project_dir = Path(__file__).resolve().parent.parent.parent
        dir = project_dir / "models" / "data" / "CALDATA"
        for file in dir.iterdir():
            if file.is_file() and file.suffix in ['.json']:
                with open(file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    print(loaded_data)
                condition_1 = (loaded_data['wall'] == self.config.wall)
                condition_2 = (loaded_data['distance_from_wall'] == self.config.distance_from_wall)
                condition_3 = (list(loaded_data['probe_position']) == list(self.config.probe_position))

                if condition_1 and condition_2 and condition_3:
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
        dir = project_dir / "models" / "data" / "CALDATA" 
        dir.mkdir(exist_ok=True)
        data = self._generate_save_metadata()
        data['vx_gain'] = self.calibrate_type.vx_gain
        data['vy_gain'] = self.calibrate_type.vy_gain
        data['vz_gain'] = self.calibrate_type.vz_gain
        self.calibration_data = data
        file_path = dir / f"Callibration_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json"
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)


    def _load_calibration(self, data: dict) -> None:
        self.calibration_data = data