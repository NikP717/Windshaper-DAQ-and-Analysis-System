import threading
import time
import logging

from models.data.WindDataset import WindDataset
from models.experiment.ExperimentConfig import ExperimentConfig

logger = logging.getLogger(__name__)

class DeviceDataManager():
    """Class which exists within DeviceManager and is dedicated to creating dataset instances for each registered device and logging data to these datasets."""
    def __init__(self,windcontroller_instance,registered_devices_list: list, config: ExperimentConfig) -> None:
        """Initialisation creates winddata instances for each device"""
        logger.info("Initialised.")
        self.registered_devices_list = registered_devices_list
        self.windcontroller = windcontroller_instance
        self.windshaper = windcontroller_instance.windwrapper
        self.config = config
        self.data_instance_dict = {}
        self._create_winddata()
        self.stop_event = threading.Event()

    def _create_winddata(self) -> None:
        """Function which assigns a WindDataset to each device."""
        for devices in self.registered_devices_list:
            self.data_instance_dict[devices] = WindDataset(self.config.manual_meta_data)

    def stop(self) -> None:
        self.stop_event.set()
    
    def set_metadata(self) -> None:
        """Function which assigns metadata to each devices winddata instance."""
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
        """Function which is used by the DeviceManager writer thread to assign buffered data lists into winddata at a lower frequency than aquisiction."""
        while not self.stop_event.is_set():
            for device, data in self.data_instance_dict.items():
                with device.buffer_lock:
                    current_buffered_data = device.current_buffer_data
                    device.current_buffer_data = []

                    if current_buffered_data:
                        data.store_buffered_probe_data(current_buffered_data)
            time.sleep(.1) # limit upload data speed compared to sampling frequency of probe 200Hz to not contest buffer lock excessively

    def save_data(self) -> None:
        """Function which converts the dictionary of each device and winddata instance to saved winddata pkl files witihn WINDDATA."""
        for device, data in self.data_instance_dict.items():
            data.crop_data_time(self.config.time_crop)
            data.save_obj()
        logger.info("Data Saved to WINDDATA, ending current instance...")