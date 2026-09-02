from models.data.ExperimentSeriesDataSet import ExperimentSeriesDataSet
from models.data.WindDataset import WindDataset
from pathlib import Path
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import regex as re
import scipy.io as sio

class WindAnalyser:
    """Class which acts as a method storage and also current analysis storage.
    Enables the user to easily analyse datasets stored within WINDANALYSIS without having to worry about paths of files.
    Enables user to easily load/save user made datasets from analysis and save figures without worrying about paths of files.

    Best way to understand this class is to see .examples.
    
    NOTE: Due to my own limited personal analysis, this class has much room for 
    improvement for accessibility/functionality and could probably form a models.analysis folder in the future"""

    experiment_name = ""
    @classmethod
    def _check_experiment_set(cls) -> None:
        """Helper function which checks if an experiment dataset is loaded prior to usage."""
        if not cls.experiment_name:
            raise ValueError("No Experiment Loaded, have you used load_experiment_dataset?")
        
    @classmethod
    def _locate_working_directory(cls) -> Path:
        """Helper function which locates the working directory of the experiment refererenced by the analyser."""
        project_dir = Path(__file__).resolve().parent.parent
        data_dir = project_dir / "WINDANALYSIS" / cls.experiment_name
        return data_dir

    @classmethod
    def load_experiment_dataset(cls,experiment_name: str) -> pd.DataFrame:
        """Function which converts Pickle file into pandas dataset of folder named experiment in WINDANALYSIS"""
        cls.experiment_name = experiment_name
        dir = cls._locate_working_directory()
        data_dir = dir / f"{experiment_name}.pkl"
        dataset_obj = ExperimentSeriesDataSet.load(data_dir)
        return dataset_obj.data_set

    @staticmethod
    def _mean_mixed(series) -> float: # for column averaging
        """Helper function which averages mixed data (listed cells and float cells)"""
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
    def _std_mixed(series) -> float: # for creating standard deivation columns
        """Helper function which finds the std of mixed data (listed cells and float cells)"""
        first_val = series.iloc[0]
        if isinstance(first_val, (list, np.ndarray, pd.Series)):
            arrays = [np.asarray(v, dtype=float) for v in series]
            max_len = max(len(a) for a in arrays)
            padded = np.vstack([np.pad(a, (0, max_len - len(a)), 'edge') for a in arrays])
            return padded.std(axis=0)
        return float(np.std(series))
    
    @staticmethod
    def _mean_circular(series) -> float:
        """Helper function which averages circular data which is wrapped via 180 (angle quantities)"""
        series = np.asarray(series.dropna(), dtype=float)
        if series.size == 0:
            return np.nan

        rad = np.deg2rad(series)
        sin_mean = np.mean(np.sin(rad))
        cos_mean = np.mean(np.cos(rad))
        return np.rad2deg(np.arctan2(sin_mean, cos_mean))

    @staticmethod
    def _std_circular(series) -> float:
        """Helper function which determines the std of data which is wrapped via 180 (angle quantities)"""
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
    def average_dataset(cls,dataset: pd.DataFrame,wrapped_angle_cols=None,groupby=None) -> pd.DataFrame:
        """Function which averages the repeat instances of configurations and collapses them into a dataset with averaged results.
        
        From each experiment repeat group converts it to one result mean with a standard deviation for error analysis:
        e.g Repeat 1,2,3 collapsed into 1 datapoint into a mean and standard deviation as an additional column for each variable"""
        # btw this function made me want to die
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
    def seperate_dataset_outliers(cls,mean_dataset,dataset,groups_to_check) -> tuple[pd.DataFrame, ...]:
        """Function which utilises a raw dataset, the mean dataset and any groups to check for outliers to determine adataset of outliers.
        These outliers are based on beyond 2 standard deviations above or below the mean of the repeat data.
        
        NOTE: Not certain of if this function truly works, to be tested."""
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

    @staticmethod
    def show_dataset_columns(dataset: pd.DataFrame) -> None:
        """Function which returns all dataset columns available in a dataset."""
        print(", ".join(dataset.columns.astype(str)))
    
    @staticmethod
    def show_dataset_summary(dataset: pd.DataFrame) -> None:
        """Function which returns a dataset summary."""
        dataset.info()

    @staticmethod
    def add_data_column(dataset: pd.DataFrame,column_name:str,column_data) -> pd.DataFrame:
        """Function which inserts an additional column into a dataset."""
        dataset[column_name] = column_data
        return dataset
    
    @staticmethod
    def add_data_row(dataset: pd.DataFrame,row_data) -> pd.DataFrame:
        """Function which adds row to existing dataframe, WARNING - row data must be in order of headers in dataframe or an error will occur"""
        try:
            new_row = pd.DataFrame([row_data],columns=dataset.columns)
            return pd.concat([dataset,new_row],ignore_index=True)
        except Exception as e:
            print(f"Error occured: {e}")
    
    @classmethod
    def plot_tool(cls,dataframe: pd.DataFrame,raw_dataframe: pd.DataFrame,x_quantity:str , y_quantity:str,xlabel:str,ylabel:str, group_by=None, plot_raw_data=False,error_bars = False,save=True,ax=None) -> plt.ax:
        """Plotting tool Function:
        Requires mean dataset and raw dataset as an input.
        x_quantity: str -> Column name from dataframe to act as x axis plot.
        y_quantity: str -> Column name from dataframe to act as y axis plot.
        group_by: str -> Column name by which properties should be grouped on the same line, FOR EXAMPLE: groupby 'probe_id' will group data plotted by which probe it was measured from.
                so if you were to plot mean_velocity vs mean_pwm and grouped by probe - you would have a line for each probe on this plot.
        ax: plt.ax object -> To plot more lines onto an existing axis object under matplotlib.pyplot.
        
        Other function inputs are self explanatory, error bars plot the standard deviation for errors."""

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
        """Function which saves the current active plt.figure instance to the current experiment directory automatically in WINDANALYSIS."""
        cls._check_experiment_set()
        dir = cls._locate_working_directory()
        output = dir / f"{file_name}.png"
        plt.savefig(output,dpi=300)

    @classmethod
    def save_analysis_dataset(cls,dataset, file_name):
        """Converts user created pandas datasets to excel files in the current experiment directory automatically in WINDANALYSIS"""
        cls._check_experiment_set()
        dir = cls._locate_working_directory()
        output = dir / f"{file_name}.xlsx"
        dataset.to_excel(output, index=False)

    @classmethod
    def save_analysis_dataset_matlab(cls, dataset, file_name):
        """Converts user created pandas datasets to MATLAB files in the current experiment directory automatically in WINDANALYSIS
        NOTE: Not tested on actual functionality for further analysis in MATLAB - because I dont use it :)"""
        cls._check_experiment_set()
        dir = cls._locate_working_directory()
        output = dir / f"{file_name}.mat"
        mat_dict = {col_name: dataset[col_name].values for col_name in dataset.columns}
        sio.savemat(output, mat_dict)
        
        
