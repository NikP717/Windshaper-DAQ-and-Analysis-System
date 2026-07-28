from models.ExperimentSeriesDataSet import ExperimentSeriesDataSet
from models.WindDataset import WindDataset
from pathlib import Path
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import correlate, correlation_lags, welch
import regex as re
import scipy.io as sio

class WindAnalyser:
    experiment_name = ""
    @classmethod
    def _check_experiment_set(cls) -> None:
        if not cls.experiment_name:
            raise ValueError("No Experiment Loaded, have you used load_experiment_dataset?")
        
    @classmethod
    def _locate_working_directory(cls) -> Path:
        project_dir = Path(__file__).resolve().parent.parent
        data_dir = project_dir / "WINDANALYSIS" / cls.experiment_name
        return data_dir

    @classmethod
    def load_experiment_dataset(cls,experiment_name: str) -> pd.DataFrame:
        """Converts Pickle file into pandas dataset of folder named experiment in WINDANALYSIS"""
        cls.experiment_name = experiment_name
        dir = cls._locate_working_directory()
        data_dir = dir / f"{experiment_name}.pkl"
        dataset_obj = ExperimentSeriesDataSet.load(data_dir)
        return dataset_obj.data_set
    
    # @classmethod
    # def load_experiment_dataset_timecropped(cls, experiment_name: str, time_1:float, time_2:float) -> pd.DataFrame:
    #     cls.experiment_name = experiment_name
    #     dir = cls._locate_working_directory()
    #     data_dir = dir / f"{experiment_name}.pkl"
    #     dataset_obj = ExperimentSeriesDataSet.load(data_dir)
    #     dataset_obj.timecrop_all_experiments(time_1,time_2)
    #     return dataset_obj.data_set

    @staticmethod
    def _mean_mixed(series): # for column averaging
        first_val = series.iloc[0]
        #  list inside the cell (for listed vars)
        if isinstance(first_val, (list, np.ndarray, pd.Series)):
            arrays = [np.asarray(v, dtype=float) for v in series]
            max_len = max(len(a) for a in arrays)
            padded = np.vstack([np.pad(a, (0, max_len - len(a)), 'edge') for a in arrays])
            return padded.mean(axis=0)
        # float in the cell
        return float(np.mean(series))

    @staticmethod
    def _std_mixed(series): # for creating standard deivation columns
        first_val = series.iloc[0]
        if isinstance(first_val, (list, np.ndarray, pd.Series)):
            arrays = [np.asarray(v, dtype=float) for v in series]
            max_len = max(len(a) for a in arrays)
            padded = np.vstack([np.pad(a, (0, max_len - len(a)), 'edge') for a in arrays])
            return padded.std(axis=0)
        return float(np.std(series))
    
    @staticmethod
    def _mean_circular(series):
        """Calculates circular mean wrapped via 180."""
        series = np.asarray(series.dropna(), dtype=float)
        if series.size == 0:
            return np.nan

        rad = np.deg2rad(series)
        sin_mean = np.mean(np.sin(rad))
        cos_mean = np.mean(np.cos(rad))
        return np.rad2deg(np.arctan2(sin_mean, cos_mean))

    @staticmethod
    def _std_circular(series):
        """Calculates circular standard deviation in degrees."""
        cleaned = np.asarray(series.dropna(), dtype=float)
        if cleaned.size == 0 or len(cleaned) == 1:
            return 0.0
        rad = np.deg2rad(cleaned)
        sin_mean = np.mean(np.sin(rad))
        cos_mean = np.mean(np.cos(rad))
        
        # R is the length of the mean resultant vector (0 to 1)
        R = np.sqrt(sin_mean**2 + cos_mean**2)
        
        # Avoid log(0) error if data points are perfectly spread out
        if R <= 1e-12:
            return np.rad2deg(np.inf)
            
        # Standard circular variance formula
        # Clamping R to 1.0 prevents tiny floating point errors making R > 1
        R = min(R, 1.0)
        circ_std_rad = np.sqrt(-2 * np.log(R))
        return np.rad2deg(circ_std_rad)

    @classmethod
    def average_dataset(cls,dataset,wrapped_angle_cols=None,groupby=None):
        """From each experiment repeat group converts it to one result mean with a standard deviation for error analysis:
        e.g Repeat 1,2,3 collapsed into 1 datapoint into a mean and standard deviation as an additional column for each variable"""
        if groupby:
            non_averaging_columns = groupby
        else:
            data_structure = WindDataset()
            non_averaging_columns = [col for col in data_structure.meta_columns if col != 'repeat']
        
        numeric_cols = [col for col in dataset.columns if col not in non_averaging_columns and col != "repeat"]
        mean_agg_dict = {}
        std_agg_dict = {}

        for col in numeric_cols:
            if wrapped_angle_cols:
                if col in wrapped_angle_cols:
                    mean_agg_dict[col] = cls._mean_circular
                    std_agg_dict[col] = cls._std_circular
                else:
                    mean_agg_dict[col] = cls._mean_mixed
                    std_agg_dict[col] = cls._std_mixed
            else:
                mean_agg_dict[col] = cls._mean_mixed
                std_agg_dict[col] = cls._std_mixed

        mean_data_frame = dataset.groupby(non_averaging_columns).agg(mean_agg_dict).reset_index()
        std_data_frame = dataset.groupby(non_averaging_columns).agg(std_agg_dict).reset_index()

        for col in numeric_cols:
            mean_data_frame[f'{col}_std'] = std_data_frame[col]
        return mean_data_frame
    
    @classmethod
    def seperate_dataset_outliers(cls,mean_dataset,dataset,groups_to_check):
        global_outlier_mask = pd.Series(False, index=dataset.index)
        for col in groups_to_check:
            repeats = dataset['repeat'].max()
            try:
                mean_data = mean_dataset[col]
                column = dataset[col].to_numpy()
                mean_data_std_col = mean_dataset[f"{col}_std"]
            except KeyError:
                raise KeyError(f"Column '{col}' not found or '{col}_std' does not exist in mean dataset.")
            
            upper_bound = ((2 * mean_data_std_col) + mean_data).to_numpy()
            lower_bound = (mean_data - (2 * mean_data_std_col)).to_numpy()
            # Lengthens outlier condition for number of repeats (turns a boundary list from (1,2,3) to (1,1,2,2,...))
            upper_bound = np.repeat(upper_bound,repeats)
            lower_bound = np.repeat(lower_bound,repeats)

            current_outlier_condition = (column > upper_bound) | (column < lower_bound)
            global_outlier_mask = global_outlier_mask | current_outlier_condition # accumulates outliers from dataset
            clean_dataset = dataset[~global_outlier_mask]
            outlier_dataset = dataset[global_outlier_mask]
        clean_mean_dataset = cls.average_dataset(clean_dataset)
        return clean_dataset, clean_mean_dataset, outlier_dataset


# import pandas as pd

# def separate_dataset_outliers(mean_dataset, dataset, groups_to_check):
#     Initialize a mask of all Falses (no outliers detected yet)
#     global_outlier_mask = pd.Series(False, index=dataset.index)
    
#     for col in groups_to_check:
#         try:
#             mean_data = mean_dataset[col]
#             column = dataset[col]
#             mean_data_std_col = mean_dataset[f"{col}_std"]
#         except KeyError:
#             raise KeyError(f"Column '{col}' or '{col}_std' missing.")
        
#         Calculate condition for the current column
#         Note: Added parentheses around arithmetic to guarantee correct pandas evaluation order
#         upper_bound = (2 * mean_data_std_col) + mean_data
#         lower_bound = mean_data - (2 * mean_data_std_col)
        
#         current_outlier_condition = (column > upper_bound) | (column < lower_bound)
        
#         Accumulate outliers across columns using OR (|)
#         global_outlier_mask = global_outlier_mask | current_outlier_condition
        
#     Split the original dataset safely AFTER checking all columns
#     Tilde (~) flips True to False, keeping standard data rows
#     clean_dataset = dataset[~global_outlier_mask]
#     outlier_dataset = dataset[global_outlier_mask]
    
#     return clean_dataset, outlier_dataset



    @staticmethod
    def show_dataset_columns(dataset: pd.DataFrame) -> None:
        print(", ".join(dataset.columns.astype(str)))
    
    @staticmethod
    def show_dataset_summary(dataset: pd.DataFrame) -> None:
        dataset.info()

    @staticmethod
    def add_data_column(dataset: pd.DataFrame,column_name:str,column_data) -> pd.DataFrame:
        dataset[column_name] = column_data
        return dataset
    
    @staticmethod
    def add_data_row(dataset: pd.DataFrame,row_data) -> pd.DataFrame:
        """Adds row to existing dataframe, WARNING - row data must be in order of headers in dataframe or an error will occur"""
        try:
            new_row = pd.DataFrame([row_data],columns=dataset.columns)
            return pd.concat([dataset,new_row],ignore_index=True)
        except Exception as e:
            print(f"Error occured: {e}")
    
    @classmethod
    def plot_tool(cls,dataframe: pd.DataFrame,raw_dataframe: pd.DataFrame,x_quantity, y_quantity,xlabel,ylabel, group_by=None, plot_raw_data=False,error_bars = False,save=True,ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=(11, 4))
            additional_label = ""
            color_index_init = 0
        else:
            fig = ax.get_figure()
            additional_label = f"({y_quantity})"
            color_index_init = 5
        sorted_dataframe = raw_dataframe.sort_values(by=x_quantity)
        if plot_raw_data:
            color_index = color_index_init
            if group_by:
                for grouped_quantity, group_df in sorted_dataframe.groupby(group_by):
                    x = group_df[x_quantity]
                    y = group_df[y_quantity]
                    ax.plot(x, y, 'x', color=f"C{color_index}", alpha=.7, markersize=4)
                    color_index += 1
            else:
                x = sorted_dataframe[x_quantity]
                y = sorted_dataframe[y_quantity]
                ax.plot(x, y, 'x', alpha=.7, markersize=4)
        color_index = color_index_init
        sorted_dataframe = dataframe.sort_values(by=x_quantity)
        if group_by:
            for grouped_quantity, group_df in sorted_dataframe.groupby(group_by):
                x = group_df[x_quantity]
                y = group_df[y_quantity]

                if not error_bars:
                    ax.plot(x, y, 'x-', label=f"{group_by}: {grouped_quantity:.2f} {additional_label}", color=f"C{color_index}")
                else:
                    x_error = group_df[f'{x_quantity}_std'] if f'{x_quantity}_std' in group_df.columns else None
                    y_error = group_df[f'{y_quantity}_std'] if f'{y_quantity}_std' in group_df.columns else None
                    if x_error is not None:
                        x_error = abs(x_error)
                    if y_error is not None:
                        y_error = abs(y_error)
                    ax.errorbar(x, y, yerr=y_error, xerr=x_error, fmt='x-',  ecolor=f"C{color_index}", color=f"C{color_index}",capsize=5, elinewidth=2,label=f"{group_by}: {grouped_quantity:.2f}")
                color_index += 1
        else:
            x = sorted_dataframe[x_quantity]
            y = sorted_dataframe[y_quantity]
            
            if not error_bars:
                ax.plot(x, y, 'x-')
            else:
                x_error = sorted_dataframe[f'{x_quantity}_std'] if f'{x_quantity}_std' in sorted_dataframe.columns else None
                y_error = sorted_dataframe[f'{y_quantity}_std'] if f'{y_quantity}_std' in sorted_dataframe.columns else None
                if x_error is not None:
                    x_error = abs(x_error)
                if y_error is not None:
                    y_error = abs(y_error)
                ax.errorbar(x, y, yerr=y_error, xerr=x_error, fmt='x-', capsize=5, elinewidth=2, ecolor="blue", color="darkblue")
        ax.legend()
        ax.grid(True)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if save:
            clean_name = re.sub(r'[\\/*?:"<>|\[\]%]', "", f"{ylabel} against {xlabel}")  
            clean_name = re.sub(r'\s+', "_", clean_name)         
            cls.save_plot(clean_name)
            plt.close()
        else:
            return fig, ax

    @classmethod
    def save_plot(cls,file_name):
        cls._check_experiment_set()
        dir = cls._locate_working_directory()
        output = dir / f"{file_name}.png"
        plt.savefig(output,dpi=300)

    @classmethod
    def save_analysis_dataset(cls,dataset, file_name):
        """Converts user created pandas datasets to excel files in the experiment analysis directory"""
        cls._check_experiment_set()
        dir = cls._locate_working_directory()
        output = dir / f"{file_name}.xlsx"
        dataset.to_excel(output, index=False)

    @classmethod
    def save_analysis_dataset_matlab(cls, dataset, file_name):
        cls._check_experiment_set()
        dir = cls._locate_working_directory()
        output = dir / f"{file_name}.mat"
        mat_dict = {col_name: dataset[col_name].values for col_name in dataset.columns}
        sio.savemat(output, mat_dict)
        
        
