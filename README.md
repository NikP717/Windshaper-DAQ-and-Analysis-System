NOTE: See Raw format for clearer code structure view.
# Purpose
This Python framework provides a layered and modular workflow for automated wind-tunnel experimentation using the WindShape WindShaper through the WindSuite SDK. It provides configurable experiment definition, wind-profile generation, data acquisition, control, calibration and structured data analysis.

# Credits
Nicholas Pedzik 03/09/2026
`windprobe_api` WindProbe API: Copyright (C)2018-2022 WindShape Ltd - All Rights Reserved, Old Probe API 

# Quick Start
1. Connect the WindProbe directly to the computer via USB.
2. Connect the WindShaper via LAN.
3. Open a terminal in the repository directory.
4. Run:

`uv run python -i ConfigureExperiment.py` OR press `RUNSCRIPT.bat`

5. Follow the example configuration to create and execute an experiment.
6. Experimental data will be stored in `WINDDATA`. (Occurs within default ConfigureExperiment Script)
7. Save a configuration series to transfer the data to `WINDANALYSIS`. (Occurs within default ConfigureExperiment Script)
8. Use `AnalyseExperiment.py` to analyse the resulting dataset.

For configurations, they can run open or closed loop control, see more in examples.

For profiles in configurations, look at `Profiles.py` for existing examples, and it is simple to create and add your own.

Once the flow profile begins the data logging begins, same applies when it ends.

# Dependencies
The scripts requires `Astral uv` to manage the libraries and run the scripts. 

You can install it on every system using [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

With this package, upon running this directory all necessary libraries will be installed automatically.

# README Definitions
- Configuration -> A single experiment ran in ConfigureExperiment.py
- Old Probe -> WindShape Series X probe (discontinued)
- New Probe -> WindShape Series A probe 
- Sim Probe -> Simulation of a Windshape Series X Probe.

# Examples

Examples can be found in the examples folder, in order to try these, please move or create a python file in the main folder (not the examples subfolder) in order for the run command to work.

Currently by default: `AnalyseExperiment.py`, `ConfigureExperiment.py` and `Profiles.py` already contain a default configuration for the user to practise using the pipeline and to better understand it.

# Hardware Requirements
**Zeroing**
    The zeroing of the pressure sensors is done when you plug the WindProbe to your computer for the Old Probe, automatically prior to experiment with the New Probe.

**Connection Requirement**
    The needs to be directly connected to the computer, not through a USB hub.
    This script requires a direct USB connection to the Probe AND a direct LAN connection to the WindShaper, LAN adapters also work here.

# Safety
**Max PWM Setting**
A Max PWM can be configured so no instruction force exceeds it on the windshaper, found under models.experiment.ExperimentSafety to modify it.
**CTRL+C**
During any experiment CTRL+C will trigger a keyboard interrupt which immediately stops the windshaper.

# Framework Structure

**User Facing Code**
    - `Profiles.py` -> Used for creation of custom wind profiles to apply to the experiment system. See more within the file.
    - `ConfigureExperiment.py` -> Used for creating experiment configurations, running series of configurations and saving configurations results.
    - `AnalyseExperiment.py` -> Used for analysing complete datasets which reside in `WINDANALYSIS` upon saving configuration series.

    For additional details on how to use each one of these files, see examples and inserted commentry in these files.

*An example configuration, analysis and profile are already inputted by default for the user to test the system workflow initially*

**Framework Tree**
    User configuration
        ↓
    WindProfile (from `Profiles.py`) / ExperimentConfig (from `ConfigureExperiment.py`)
        ↓
    ExperimentRunner ├── *WindTracker (if initialised)
        ↓
    DeviceManager
        ├── ExperimentClock
        │
        ├── WindController
        │      ├── WindProfileBuilder
        │      ├── *ClosedLoopControlManager (if initialised)
        │      │      ├── *VelocityControl
        │      │      ├── *TurbulenceControl
        │      │      └── *TurbulenceSpectralControl
        │      │          └── PIDController Instances
        │      └── WindsuiteManager
        │             └── WindSuite SDK
        │
        ├── Probe devices
        │      ├── OldProbe
        │      ├── NewProbe
        │      └── SimProbe
        │           └── *LivePlotter Instances (if initialised)
        │
        └── DeviceDataManager
                ↓
            WindDataset Instances
                ↓
        ExperimentSeriesDataSet **(if save_configuration_series is ran)**
                ↓
            Analysis

    The code also uses several Data Feedback storage for experiment running: ControlFeedbackState, ProbeFeedbackState, WindState

**Folder Structure**
    `models` -> Where all non-user facing code resides.
    `WINDDATA` -> Where all WindDataSet Instances are stored prior to saving as a configuration series.
    `WINDANALYSIS` -> Where all configuration series are saved.
    `WINDCALDATA` -> Where all calibrations are stored as JSONS **if you insert this feature into closedloop control** -> currently not in use.

**Data Pipeline and Hierarchy**
    (WindState Feedback + Probe Data) → WindDataset → pkl File in `WINDDATA` 
    → ConfigureExperiment.save_configuration_series(name) → ExperimentSeriesDataSet → Folder in `WINDANALYSIS` containing pkl file + raw data 
    
    - Upon saving a configuration series - ALL WINDDATA PKL FILES - are transferred to WINDANALYSIS under the new configuration series name.
    - HELPFUL: If the user saves a configuration series name which already exists, the directory within WINDANALYSIS automatically merges the new data with the existing one.
    - By default .pkl files are used for easy python object wrapping/unwrapping from file however user can opt to also save in excel format for data readability.

    WindDataSet: 
        - Contains probe_data columns, meta_data columns, summary_data columns -> see models.data.DataColumns for more details on columns.
        - Each row of data within probe_data is a sample from the probe.
        - WindDatasets prior to saving calculate summary data statistics and store them under summary_data.
    
    ExperimentSeriesDataSet:
        - Contains probe_data_list columns, meta_data columns, summary_data columns -> see models.data.DataColums and models.data.ExperimentSeriesDataSet.__init__()
        - Each row of data is a single WindDataset collapsed into a row (one configuration)
        - List columns contain arrays of time series measurements, for example: windspeed_x_list contains all velocity samples in x direction for that configuration / row.
    
**Quantities**
    This script automatically calculates the following quantities and attaches it to raw probe data: 
    Mean Velocity **[m/s]** , Velocity Standard Deviation **[m/s]** , Turbulence Intensity **[%]** , 
    Rolling Mean and Standard deviation, and P Value (statistical).
    For more details see models.data.WindDataset

    Raw Probe Data takes on the following form:
    Time **[s]**, Ux **[m/s]**, Uy  **[m/s]**, Uz  **[m/s]**, pstat  **[Pa]**, Temperature **[°C]**, Atmospheric pressure **[hPa]**

    Attached beside the Raw Probe Data and calculated quantities is the live windshaper statistics
    Average PWM **[%]**, Average RPM **[%]**, Average Target PWM **[%]**, PWM Standard Deviation **[%]**, RPM Standard Deviation **[%]**

    These form the columns in individual `WINDDATA` instances.

    These columns can be customised by following information within models.data.DataColumns.

## Data Analysis

This script also simplifies and enables the user to load experimental datasets once they have been saved with ease for analysis.

Any function which saves plots or exports tables is automatically depositing this information to the same `WINDANALYSIS` folder the user names in code.

For more details of analysis see the examples folder for a few examples using sample data from running the repository default experiment code in `WINDANALYSIS`.

You can optionally also export analysis tables and datasets to EXCEL and MATLAB compatible files.

## Known Limitations and Future Work
For future use on any person expanding this repository further. Any contribution is appreciated!!

- Multi device support where devices are identical (e.g two New Probes) has not been tested nor accounted for, something to work on.
- New Probe Tracking has not been implemented, so will not work (need a specific object name from Motive/Camera Tracking - see TODO in models.WindTracker)
- Closed loop control only works for the WHOLE fan array, not control of individual fans which is another issue - something to work on.
- Closed loop control also doesnt have a specific system in place for displaying controller feedback, logical step forward for configuring controllers in future.
- Calibration is currently not used in ClosedLoopControl due to cross-coupling and non linearity in turbulence not making it forseeable at the minute. However all necessary        features are in place for easier implementation (saving and loading from WINDCALDATA exists alongside a velocity calibration and base calibration example.)

- WindAnalysis is an early stage model for future analysis pipelines, could likely become its own folder if expanded on - this framework has not been used much for analysis.
- SpectralControl and TurbulenceControl has the framework in place, but has not been tuned/adjusted or even fixed framework wise to function efficiently with accuracy.
- This code has some configuration, profile checking features but potentially is not fully robust.
- Overall this code has not been thoroughly tested with different users so many weakpoints may exist.
