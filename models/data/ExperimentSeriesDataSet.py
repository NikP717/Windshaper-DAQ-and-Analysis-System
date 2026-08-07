import pandas as pd
from pathlib import Path
import shutil
import pickle
from models.data.DataColumns import DataColumns
from models.data.WindDataset import WindDataset

from typing import Self

class ExperimentSeriesDataSet:
    def __init__(self, name: str) -> None:
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
        self.list_columns = [f"{c}_list" for c in DataColumns.PROBE_COLUMNS]
        
        self.data_set = None
        self.name = name
        self.processed_files = []
        self._rows = []

    def _add_experiment(self,data: WindDataset) -> None:
        listed_vars = []
        # list variables, e.g velocity over time instead of just average as defined above in columns
        keys = data.probe_data.columns
        for key in keys:
            listed_vars.append(data.probe_data[key].tolist()) 
        data_row = data.compact_data_to_row()
        listed_vars.extend(data_row)
        self._rows.append(listed_vars)

    def input_winddata(self) -> None:
        project_dir = Path(__file__).resolve().parent.parent.parent
        data_dir = project_dir / "WINDDATA"

        for path in data_dir.iterdir():
             if path.is_file() and path.suffix in ['.pkl']:
                  winddata = WindDataset.load(path)
                  self._add_experiment(winddata)
                  new_path = winddata.save_to_xl()
                  self.processed_files.append(new_path)
                  self.processed_files.append(path)

    def save(self, remove_raw_data: bool = False) -> None:
        # WINDANALYSIS
        # > EXPERIMENT NAME (FOLDER)
        # > > EXCEL SHEET OF OVERALL DATA SET
        # > > PICKLED OBJECT CLASS IF BEING LOADED LATER
        # > > RAWDATA (FOLDER)
        # > > > ALL EXPERIMENTAL DATA USED FOR EACH EXPERIMENT IN EXCEL FORM
        """Only use for newly created experimental data, forcefully moves Winddata used into this new instance"""

        project_dir = Path(__file__).resolve().parent.parent.parent
        output_dir = project_dir / "WINDANALYSIS" / self.name # experiment folder in wind analysis
        raw_data_output = output_dir / "RAWDATA" 
        raw_data_output.mkdir(parents=True, exist_ok=True)

        for paths in self.processed_files:
             if paths.exists():
                if remove_raw_data:
                    paths.unlink()
                else:
                    shutil.move(paths, raw_data_output)

        self.data_set = pd.DataFrame(self._rows, columns=self.columns)
        self._rows.clear() # saves data storage
        self.processed_files.clear() # saves data storage
        self._save_obj(output_dir)
        self._save_to_xl(output_dir)

    def _save_obj(self, output_dir: Path) -> None:
        """Saves object class as a pickle instance"""
        output = output_dir / self.name
        with open(f"{output}.pkl","wb") as file:
            pickle.dump(self, file)
             
    def _save_to_xl(self, output_dir: Path) -> None:
        """"
        Creates an excel representation for data, does not include listed variables due to excel parsing large quantities of text.
        Load from excel makes listed variables hard to use, recommend using load function instead""" 
        file_name = f"{self.name}.xlsx" # excel sheet identical name as folder its within
        output = output_dir / file_name
        df_no_lists = self.data_set.drop(columns=self.list_columns)

        with pd.ExcelWriter(output) as writer:
            df_no_lists.to_excel(writer, sheet_name="overall_data", index=False)

    @classmethod
    def load(cls,path: Path) -> Self:
        """Loads complete dataset object"""
        with open(path, "rb") as file:
            loaded_object = pickle.load(file)
            return loaded_object
    @classmethod
    def load_from_xl(cls,path: Path) -> Self:
        """[!] Creates data set object which does not include listed variables e.g time elpased, velocity elapsed etc."""
        filename = Path(path).stem
        new_data_obj = cls(name=filename)
        excel_data = pd.read_excel(path, sheet_name=None)
        new_data_obj.data_set = excel_data.get("overall_data")
        return new_data_obj
