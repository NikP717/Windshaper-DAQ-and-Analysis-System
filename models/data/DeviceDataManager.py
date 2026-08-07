import threading
import time
from models.data.WindDataset import WindDataset
from models.experiment.ExperimentConfig import ExperimentConfig

class DeviceDataManager():
    def __init__(self,windcontroller_instance,registered_devices_list: list, config: ExperimentConfig) -> None:
        self.registered_devices_list = registered_devices_list
        self.windcontroller = windcontroller_instance
        self.windshaper = windcontroller_instance.windwrapper
        self.config = config
        self.data_instance_dict = {}
        self._create_winddata()
        self.stop_event = threading.Event()

    def _create_winddata(self) -> None:
        for devices in self.registered_devices_list:
            self.data_instance_dict[devices] = WindDataset(self.config.manual_meta_data)

    def set_metadata(self) -> None:
        for device, data in self.data_instance_dict.items():
            if not self.config.manual_meta_data:
                array_state = self.windshaper.array_state
                meta_data = {'probe_id':device.ID,
                            'upstream_pwm':array_state.current_avg_upstream_pwm_instr,
                            'downstream_pwm':array_state.current_avg_downstream_pwm_instr,
                            'distance_from_wall':self.config.distance_from_wall,
                            'probe_pos_x':self.config.probe_position[0],
                            'probe_pos_y':self.config.probe_position[1],
                            'repeat':self.config.repeat}
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

    def save_data(self) -> None:
        for device, data in self.data_instance_dict.items():
            data.crop_data_time(self.config.time_crop)
            data.save_obj()
        print("[DEVICEDATAMANAGER] Data Saved to WINDDATA, ending current instance...")