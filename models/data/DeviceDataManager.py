import threading
import time
from models.data.WindDataset import WindDataset
from models.data.ExperimentSeriesDataSet import ExperimentSeriesDataSet
from models.experiment.ExperimentConfig import ExperimentConfig

class DeviceDataManager():
    def __init__(self,registered_devices_list: list, config: ExperimentConfig):
        self.registered_devices_list = registered_devices_list
        self.config = config
        self.data_instance_dict = {}
        self._create_winddata()
        self.stop_event = threading.Event()

    def _create_winddata(self):
        for devices in self.registered_devices_list:
            self.data_instance_dict[devices] = WindDataset(self.config.manual_meta_data)

    def set_metadata(self):
        for device, data in self.data_instance_dict.items():
            if not self.config.manual_meta_data:
                meta_data = {'probe_id':device.ID,
                            'fan_pwm':self.windshaper.pwm_instructions,
                            'upstream_pwm':self.windshaper.pwm_upstream_instr,
                            'downstream_pwm':self.windshaper.pwm_downstream_instr,
                            'distance_from_wall':self.config.distance_from_wall,
                            'probe_pos_x':self.config.probe_position[0],
                            'probe_pos_y':self.config.probe_position[1],
                            'repeat':self.config.repeat,
                            'wind_fq':self.windshaper.windfunct_fq,
                            'wind_amplitude':self.windshaper.windfunct_amplitude,
                            'wind_avg':self.windshaper.windfunct_average}
            else:
                meta_data = self.config.manual_meta_data
                meta_data['repeat'] = self.config.repeat
                meta_data['probe_id'] = device.ID

            data.set_meta_data(meta_data)

    def update_dataset_thread(self) -> None:
            while not self.stop_event.is_set():
                for device, data in self.data_instance_dict.items():
                    with device.buffer_lock:
                        current_buffered_data = device.current_buffer_data
                        device.current_buffer_data = []

                        if current_buffered_data:
                            data.store_buffered_probe_data(current_buffered_data)
                time.sleep(.1) # limit upload data speed compared to sampling frequency of probe 200Hz to not contest buffer lock excessively

    def save_data(self):
        for device, data in self.data_instance_dict.items():
            data.crop_data_time(self.config.time_crop)
            data.save_to_xl()
        print("[DEVICEDATAMANAGER] Data Saved to WINDDATA, ending current instance...")