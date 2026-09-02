import pandas as pd
from pathlib import Path
import shutil
import pickle
from typing import Self

from models.data.DataColumns import DataColumns
from models.data.WindDataset import WindDataset

class ExperimentSeriesDataSet:
    """Class which stores WindDataset instances as row-data lines in a larger dataset. Each row is a Winddataset output, this class enables large
    dataset analysis later on."""
    def __init__(self, name: str) -> None:
        """Initialises data columns, saving directory and referenced meta data."""
        project_dir = Path(__file__).resolve().parent.parent.parent
        reference_meta_file = next((project_dir / "WINDDATA").glob("*.pkl"))
        meta_data_cols = WindDataset.load(reference_meta_file).meta_data.columns.tolist() # takes a WINDDATA file metadata, important for all winddata files to have identical metadata

        self.columns = (
            [f"{c}_list" for c in DataColumns.PROBE_COLUMNS]
            + meta_data_cols
            + [f"{c}_x" for c in DataColumns.SUMMARY_COLUMNS]
            + [f"{c}_y" for c in DataColumns.SUMMARY_COLUMNS]
            + [f"{c}_z" for c in DataColumns.SUMMARY_COLUMNS]
            + [f"{c}_3d" for c in DataColumns.SUMMARY_COLUMNS]
            )
        self.list_columns = [f"{c}_list" for c in DataColumns.PROBE_COLUMNS] # list columns store time series and velocity series data as a list.
        
        self.data_set = None
        self.name = name
        self.processed_files = []
        self._rows = []

    def _add_experiment(self,data: WindDataset) -> None:
        """Function which adds a WindDataset as a row onto the parent class dataset."""
        listed_vars = []
        # list variables, e.g velocity over time instead of just average as defined above in columns
        keys = data.probe_data.columns
        for key in keys:
            listed_vars.append(data.probe_data[key].tolist()) 
        data_row = data.compact_data_to_row()
        listed_vars.extend(data_row)
        self._rows.append(listed_vars)

    def input_winddata(self) -> None:
        """Function which adds Winddatasets to the parent class dataset and records the file process and saves an excel instance of winddata for user reference."""
        project_dir = Path(__file__).resolve().parent.parent.parent
        data_dir = project_dir / "WINDDATA"

        for path in data_dir.iterdir():
             if path.is_file() and path.suffix in ['.pkl']:
                  winddata = WindDataset.load(path)
                  self._add_experiment(winddata)
                  new_path = winddata.save_to_xl()
                  self.processed_files.append(new_path)
                  self.processed_files.append(path)

    def save(self, save_to_excel: bool = True, remove_raw_data: bool = False) -> None:
        """Function which saves the ExperimentSeriesDataSet instance as a pkl file storing the dataset and processed files in WINDANALYSIS,
        it also moves all processed files into a RAWDATA file for reference too.
        
        NOTE: If a similar ExperimentSeriesDataset with an identical name has previously been saved, this function merges the two datasets together.
        This feature prevents dataloss due to data overwriting, and allows users to save additional winddata seamlessly to existing datasets.

        NOTE: Moves ALL data within WINDDATA > This data set instance. If any meta data is mismatched, pandas will exhibit unexpected behaviour.
        
        The data path of everything saved is presented below:
        # .WINDANALYSIS
        #   > EXPERIMENT NAME (FOLDER)
        #       > > EXCEL SHEET OF OVERALL DATA SET (IF USER ENABLED EXCEL)
        #       > > PICKLED OBJECT CLASS IF BEING LOADED LATER
        #       > > RAWDATA (FOLDER)
        #            > > > ALL EXPERIMENTAL DATA USED FOR EACH EXPERIMENT IN EXCEL FORM UNLESS EXCEL SAVING IS DISABLED
        """

        project_dir = Path(__file__).resolve().parent.parent.parent
        output_dir = project_dir / "WINDANALYSIS" / self.name # experiment folder in wind analysis
        raw_data_output = output_dir / "RAWDATA" 
        try:
            raw_data_output.mkdir(parents=True)
        except FileExistsError:
            self._merge_datasets(path=output_dir/f"{self.name}.pkl")
            for file in raw_data_output.iterdir():
                if file.suffix in [".pkl",".xlsx"]:
                    shutil.move(file, project_dir / "WINDDATA") # moves back to winddata so other datasets paths of processed files is valid
            shutil.rmtree(output_dir) # delete old
            raw_data_output.mkdir(parents=True) # create new
        
        for paths in self.processed_files:
             if paths.exists():
                if remove_raw_data:
                    paths.unlink()
                else:
                    shutil.move(paths, raw_data_output)

        self.data_set = pd.DataFrame(self._rows, columns=self.columns)
        self._rows.clear() # saves data storage
        self._save_obj(output_dir)
        if save_to_excel:
            self._save_to_xl(output_dir)

    def _merge_datasets(self, path: Path):
        """Helper function which merges datasets under saving if an identical dataset is detected."""
        other_dataset = self.load(path) # initiate classmethod to produce another instance of self
        other_rows = other_dataset.data_set.values.tolist()
        self._rows.extend(other_rows)
        self.processed_files.extend(other_dataset.processed_files)

    def _save_obj(self, output_dir: Path) -> None:
        """Saves object class as a pickle instance"""
        output = output_dir / self.name
        with open(f"{output}.pkl","wb") as file:
            pickle.dump(self, file)
             
    def _save_to_xl(self, output_dir: Path) -> None:
        """"
        Creates an excel representation for data, does not include listed variables due to excel parsing large quantities of text.
        Load from excel makes listed variables hard to use, recommend using load pkl function instead""" 
        file_name = f"{self.name}.xlsx" # excel sheet identical name as folder its within
        output = output_dir / file_name
        df_no_lists = self.data_set.drop(columns=self.list_columns)

        with pd.ExcelWriter(output) as writer:
            df_no_lists.to_excel(writer, sheet_name="overall_data", index=False)

    @classmethod
    def load(cls,path: Path) -> Self:
        """Class method which loads an ExperimentSeriesDataSet object from a pkl instance."""
        with open(path, "rb") as file:
            loaded_object = pickle.load(file)
            return loaded_object
    @classmethod
    def load_from_xl(cls,path: Path) -> Self:
        """Class method which creates ExperimentSeriesDataSet object - 
        [!] NOTE: Does not include listed variables e.g time elpased, velocity elapsed etc. 
        - due to native excel storage limitations not allowing these to be inserted in the first place (cell character limit)."""
        filename = Path(path).stem
        new_data_obj = cls(name=filename)
        excel_data = pd.read_excel(path, sheet_name=None)
        new_data_obj.data_set = excel_data.get("overall_data")
        return new_data_obj
