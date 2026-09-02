from pandas import DataFrame
import pandas as pd
from pathlib import Path
import numpy as np
from statsmodels.tsa.stattools import adfuller
from datetime import datetime
import pickle
from typing import Self
import logging

from models.data.DataColumns import DataColumns

logger = logging.getLogger(__name__)

class WindDataset:
    """Class which stores inputted buffered data from DeviceManager writing thread and formats it within a pandas dataframe.
    Class also post-processes summary data and saves by default to WINDDATA. A row of winddata is a single sample from the probe."""
    def __init__(self, manual_meta: bool = False) -> None:
        """Initialises columns, metadata and summary datasets."""
        self.probe_columns = DataColumns.PROBE_COLUMNS
        self.meta_columns = DataColumns.META_COLUMNS
        self.summary_columns = DataColumns.SUMMARY_COLUMNS
        
        self.manual_meta = manual_meta
        self.probe_data = DataFrame(columns = self.probe_columns)

        if not self.manual_meta:
            self.meta_data = DataFrame(columns = self.meta_columns)
        else:
            self.meta_data = DataFrame(columns = ['probe_id','repeat',*self.manual_meta.keys()])

        self.summary_data_x = DataFrame(columns = self.summary_columns)
        self.summary_data_y = DataFrame(columns = self.summary_columns)
        self.summary_data_z = DataFrame(columns = self.summary_columns)
        self.summary_data_3d = DataFrame(columns = self.summary_columns)

        # Flag
        self.cropped_status = False

        # NOTE: Summary Data Analysis Parameters - currently hardcoded
        self.rolling_window_seconds = 3
        self.max_lag_seconds = 10
        self.convection_speed = None
    
    def set_meta_data(self,meta_data_row: list) -> None:
        """Function which sets the meta dataset for Winddata."""
        self.meta_data.loc[len(self.meta_data)] = meta_data_row
    
    def store_buffered_probe_data(self,buffer_data: list):
        """Function which converts inputted buffer data and transfers it to a new sample row in Winddataset."""
        if self.cropped_status: 
            # prevent buffer data being stored after the data has been cropped in event of remaining buffers
            # NOTE: I feel as if this is a temporary solution to a different problem of buffer writing thread not merging properly but not addressed yet.
            return
        new_rows = pd.DataFrame(buffer_data, columns=self.probe_data.columns)
        # fix any errors in data
        for col in ["windspeed_x", "windspeed_y", "windspeed_z"]:
            new_rows[col] = pd.to_numeric(new_rows[col], errors="coerce")
        self.probe_data = pd.concat([self.probe_data, new_rows], ignore_index=True)

    def crop_data_time(self, timeframe: tuple) -> None:
        """Function which uses experiment configuration specified timeframes and cuts the data to that specification."""
        self.cropped_status = True
        df = self.probe_data
        init_time = timeframe[0]
        final_time = timeframe[1]
        cropped_probe_data = df[(df['time_s'] >= init_time) & (df['time_s'] <= final_time)]
        self.probe_data = cropped_probe_data

    def _generate_summary_data(self) -> None:
        """Function which populates summary datasets using existing time-cropped stored probe dataset.
        Calculates:
        - Mean velocity in all axis.
        - Standard deviation of velocity in all axis.
        - Sampling frequency. (not stored in data).
        - Turbulence intensity in all axis and 3D Turbulence intensity.
        - Signal stationarity (see function calculating below for more details.)"""

        # Clear all summary datasets in event of remaining data.
        self.summary_data_x = self.summary_data_x.iloc[0:0]
        self.summary_data_y = self.summary_data_y.iloc[0:0]
        self.summary_data_z = self.summary_data_z.iloc[0:0]
        self.summary_data_3d = self.summary_data_3d.iloc[0:0] 
        summary_row_x = []
        summary_row_y = []
        summary_row_z = []
        summary_row_3d = []

        # Probe data for calculations
        time = self.probe_data['time_s']
        ux = self.probe_data['windspeed_x']
        uy = self.probe_data['windspeed_y']
        uz = self.probe_data['windspeed_z']

        fq_sampling = self._get_sampling_frequency(time)
        statistics_3d = self._basic_component_statistics(ux,uy,uz)

        # Ugly for loop which stores all summary statistics
        for components, summary_rows in zip(["x","y","z","3d"],[summary_row_x,summary_row_y,summary_row_z,summary_row_3d]):
            if components != "3d":
                summary_rows.append(statistics_3d[f'U{components}'])
                summary_rows.append(statistics_3d[f'sig{components}'])
                summary_rows.append(statistics_3d[f'TI{components}'])
            else:
                summary_rows.append(statistics_3d[f"Umag"])
                summary_rows.append(statistics_3d[f"sig3d"]) 
                summary_rows.append(statistics_3d[f"TI3D"])

        # Ugly for loop which calculates and stores all stationarity checks on signal.
        for velocities, summary_rows,components in zip([ux,uy,uz],[summary_row_x,summary_row_y,summary_row_z],["x","y","z"]):
            rmv, rsv, adf = self._stationarity_check(velocities, fq_sampling)
            summary_rows.extend([rmv,rsv,adf])

        summary_row_3d.extend([0,0,0]) # TODO: not sure if we can plot additional values for 3d yet, zeroed by default for now.

        # Write to data sets
        new_row_x = pd.DataFrame([summary_row_x], columns=self.summary_columns)
        new_row_y = pd.DataFrame([summary_row_y], columns=self.summary_columns)
        new_row_z = pd.DataFrame([summary_row_z], columns=self.summary_columns)
        new_row_3d = pd.DataFrame([summary_row_3d], columns=self.summary_columns)
        self.summary_data_x = pd.concat([self.summary_data_x, new_row_x], ignore_index=True)
        self.summary_data_y = pd.concat([self.summary_data_y, new_row_y], ignore_index=True)
        self.summary_data_z = pd.concat([self.summary_data_z, new_row_z], ignore_index=True)
        self.summary_data_3d = pd.concat([self.summary_data_3d, new_row_3d], ignore_index=True)

    def compact_data_to_row(self) -> list:
        """Function which is utilised by ExperimentSeriesDataSet to compact all WindDataSet data into a single row.
        This is for hierarchal data arrangement where prior to this function one row is one sample, afterwards one row is one dataset."""
        row_values = []
        if len(self.meta_data) > 0:
            row_values.extend(self.meta_data.iloc[-1].tolist())
        if len(self.summary_data_x) > 0:
            row_values.extend(self.summary_data_x.iloc[-1].tolist())
        if len(self.summary_data_y) > 0:
            row_values.extend(self.summary_data_y.iloc[-1].tolist())
        if len(self.summary_data_z) > 0:
            row_values.extend(self.summary_data_z.iloc[-1].tolist())
        if len(self.summary_data_3d) > 0:
            row_values.extend(self.summary_data_3d.iloc[-1].tolist())
        return row_values

    def save_obj(self) -> None:
        """Function which saves object class as a pickle instance"""
        project_dir = Path(__file__).resolve().parent.parent.parent
        metadata_values = self.meta_data.iloc[0]
        output_dir = project_dir / "WINDDATA" 
        if self.manual_meta:
            experiment_name = f"PRB{str(metadata_values['probe_id']).replace('.','_')}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_R{metadata_values['repeat']}"
        else:
            experiment_name = f"PRB{str(metadata_values['probe_id']).replace('.','_')}_PWMU{int(metadata_values['upstream_pwm'])}D{int(metadata_values['downstream_pwm'])}_DST{str(metadata_values['distance_from_wall']).replace('.','_')}_X{metadata_values['probe_pos_x']}_Y{metadata_values['probe_pos_y']}_R{metadata_values['repeat']}"
        filename = output_dir / f"{experiment_name}.pkl"
        self._generate_summary_data()
        with open(filename,"wb") as file:
            pickle.dump(self, file)

    @classmethod
    def load(cls,path: Path) -> Self:
        """Function which loads complete Winddataset object from a pkl file in WINDDATA."""
        with open(path, "rb") as file:
            loaded_object = pickle.load(file)
            return loaded_object

    def save_to_xl(self) -> Path: 
        """Function which saves winddataset to an excel file in WINDDATA."""
        project_dir = Path(__file__).resolve().parent.parent.parent
        output_dir = project_dir / "WINDDATA" 
        metadata_values = self.meta_data.iloc[0]
        # self._generate_summary_data() -> in the way this code works summary data already exists.
        if self.manual_meta:
            experiment_name = f"PRB{str(metadata_values['probe_id']).replace('.','_')}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_R{metadata_values['repeat']}"
        else:
            experiment_name = f"PRB{str(metadata_values['probe_id']).replace('.','_')}_PWMU{int(metadata_values['upstream_pwm'])}D{int(metadata_values['downstream_pwm'])}_DST{str(metadata_values['distance_from_wall']).replace('.','_')}_X{metadata_values['probe_pos_x']}_Y{metadata_values['probe_pos_y']}_R{metadata_values['repeat']}"
        file_name = f"{experiment_name}.xlsx"
        output = output_dir / file_name

        with pd.ExcelWriter(output) as writer:
            self.meta_data.to_excel(writer, sheet_name="meta_data", index=False)
            self.probe_data.to_excel(writer, sheet_name="probe_data", index=False)
            self.summary_data_x.to_excel(writer, sheet_name="summary_data_x", index=False)
            self.summary_data_y.to_excel(writer, sheet_name="summary_data_y", index=False)
            self.summary_data_z.to_excel(writer, sheet_name="summary_data_z", index=False)
            self.summary_data_3d.to_excel(writer, sheet_name="summary_data_3d", index=False)
        return output

    @classmethod
    def load_from_xl(cls, path: Path) -> Self: # NO DEFAULT PATH
        """Class function which loads a WindDataSet excel file into a WindDataSet instance."""
        new_data_obj = cls()
        excel_data = pd.read_excel(path, sheet_name=None)
        new_data_obj.meta_data = excel_data.get("meta_data")
        new_data_obj.probe_data = excel_data.get("probe_data")
        new_data_obj.summary_data_x = excel_data.get("summary_data_x")
        new_data_obj.summary_data_y = excel_data.get("summary_data_y")
        new_data_obj.summary_data_z = excel_data.get("summary_data_z")
        new_data_obj.summary_data_3d = excel_data.get("summary_data_3d")
        return new_data_obj
    
    def _get_sampling_frequency(self, time: np.ndarray) -> float:
        """Helper function which obtains and reports to user on the probes sampling frequency."""
        dt = np.median(np.diff(time))
        if not np.isfinite(dt) or dt <= 0:
            return 0
        fs_hz = 1.0 / dt
        logger.info(f"Achieved Sampling Frequency: {fs_hz:.2f}Hz, Probe ID: {self.meta_data['probe_id'].iloc[0]}")
        return fs_hz
    
    def _basic_component_statistics(self, ux, uy, uz) -> tuple[float, ...]:
        """Function which calculate means, fluctuations, standard deviations, and turbulence intensities and handles edge cases."""

        ux = pd.to_numeric(ux, errors="coerce").fillna(0).to_numpy()
        uy = pd.to_numeric(uy, errors="coerce").fillna(0).to_numpy()
        uz = pd.to_numeric(uz, errors="coerce").fillna(0).to_numpy()

        Ux = np.mean(ux)
        Uy = np.mean(uy)
        Uz = np.mean(uz)

        Umag = np.sqrt(Ux**2 + Uy**2 + Uz**2)

        ux_p = ux - Ux
        uy_p = uy - Uy
        uz_p = uz - Uz

        sigx = np.std(ux_p, ddof=1) if len(ux_p) > 1 else 0
        sigy = np.std(uy_p, ddof=1) if len(uy_p) > 1 else 0
        sigz = np.std(uz_p, ddof=1) if len(uz_p) > 1 else 0
        sig3d = np.sqrt(sigx**2 + sigy**2 + sigz**2)

        TIx = ((sigx / Umag) * 100) if Umag != 0 else 0
        TIy = ((sigy / Umag) * 100) if Umag != 0 else 0
        TIz = ((sigz / Umag) * 100) if Umag != 0 else 0
        TI3D = np.sqrt((sigx**2 + sigy**2 + sigz**2) / 3) * 100 / Umag if Umag != 0 else 0

        return {
        "Ux": Ux, "Uy": Uy, "Uz": Uz, "Umag": Umag,
        "ux_p": ux_p, "uy_p": uy_p, "uz_p": uz_p,
        "sigx": sigx, "sigy": sigy, "sigz": sigz, "sig3d": sig3d,
        "TIx": TIx, "TIy": TIy, "TIz": TIz, "TI3D": TI3D
        }
    
    def _stationarity_check(self,velocity_signal: np.ndarray, fs_hz: float) -> tuple[float, ...]:
        """Rolling mean and rolling standard deviation, plus optional ADF test.
        NOTE: This function was provided by Assistant Prof. Reda Snaiki (and likely AI Generated)
        
        Generates a P value for certainty of the stationary of the signal, if velocity is not steady P value will tend to be larger.
        (atleast it should - not tested thoroughly)"""

        velocity_signal = np.nan_to_num(velocity_signal, nan=0.0)
        window = max(int(self.rolling_window_seconds * fs_hz), 5)
        s = pd.Series(velocity_signal)

        rolling_mean = s.rolling(window, center=True).mean().to_numpy()
        rolling_std = s.rolling(window, center=True).std().to_numpy()

        rm = rolling_mean[np.isfinite(rolling_mean)]
        rs = rolling_std[np.isfinite(rolling_std)]

        rolling_mean_variation = np.std(rm) / np.mean(np.abs(rm)) if len(rm) > 0 and np.mean(np.abs(rm)) != 0 else 0
        rolling_std_variation = np.std(rs) / np.mean(rs) if len(rs) > 0 and np.mean(rs) != 0 else 0
        # guard against short velocity signals
        if len(velocity_signal) < 10:
            return rolling_mean_variation, rolling_std_variation, np.nan

        # guard against any ADF error
        step = max(1, len(velocity_signal) // 5000)
        try:
            adf_pvalue = adfuller(velocity_signal[::step])[1]
        except Exception:
            adf_pvalue = np.nan

        return rolling_mean_variation, rolling_std_variation, adf_pvalue




    
