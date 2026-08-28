# Purpose

This script enables the user to create experiments, encode metadata, use any amount of datalogging equipment supported to generate datasets that are easily accessible, structured and analysed. Additional features include: Custom wind profile builder, analysing tools, Live Telemetry plotting for debugging, Closed Loop Control and Calibration.

# Credits
Nicholas Pedzik 12/08/2026
`windprobe_api` WindProbe API: Copyright (C)2018-2022 WindShape Ltd - All Rights Reserved, Old Probe API 

# Dependencies
The scripts requires `Astral uv` to manage the libraries and run the scripts. 

You can install it on every system using [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

With this package, upon running this directory all necessary libraries will be installed automatically.

# Zeroing

The zeroing of the pressure sensors is done when you plug the WindProbe to your computer for the Old Probe, automatically prior to experiment with the New Probe.

# USB

The probe needs to be directly connected to the computer, not through a USB hub.

## How to run

Open a terminal in this directory and enter `uv run python -i ConfigureExperiment.py`

You may run any configuration file of your choice however this is the default, see examples for how to create your own experiment configurations.

# Examples

Examples can be found in the examples folder, in order to try these, please move or create a python file in the main folder (not the examples subfolder) in order for the run command to work.

# How to Operate

This script requires a direct USB connection to the Probe AND a direct LAN connection to the WindShaper, LAN adapters also work here.

For configurations, they can run open or closed loop control, see more in examples.

For profiles in configurations, look at `Profiles.py` for existing examples, and it is simple to create and add your own.

Once the flow profile begins the data logging begins, same applies when it ends.

## Data Handling and formatting

This script automatically deposists single configuration data from an experiment to an excel file in `WINDDATA`.

If you force a save experiment at the end of running a series of configurations, all `WINDDATA` files are moved and converted to an experiment folder in `WINDANALYSIS`.

These two processes follow a structured formatting:
Dataframes in `WINDDATA` have a row for each sample.
Dataframes in `WINDANALYSIS` have a row for each configuration (series of samples).

Dataframe structures can be observed with commands, see analysis examples. All analysis done using the WindAnalyser tool will save dataframes and figures automaitcally to its respective `WINDANALYSIS` folder.

# Quantities
This script automatically calculates the following quantities and attaches it to raw probe data: 
Mean Velocity **[m/s]** , Velocity Standard Deviation **[m/s]** , Turbulence Intensity **[%]** , 
Rolling Mean and Standard deviation (statistical).

Raw Probe Data takes on the following form:
Time **[s]**, Ux **[m/s]**, Uy  **[m/s]**, Uz  **[m/s]**, pstat  **[Pa]**, Temperature **[°C]**, Atmospheric pressure **[hPa]**

Attached beside the Raw Probe Data and calculated quantities is the live windshaper statistics
Average PWM **[%]**, Average RPM **[%]**, Average Target PWM **[%]**, PWM Standard Deviation **[%]**, RPM Standard Deviation **[%]**

These form the columns in individual `WINDDATA` instances.
---------------------------------------------------

## Data Analysis

This script also simplifies and enables the user to load experimental datasets once they have been saved with ease for analysis.

Any function which saves plots or exports tables is automatically depositing this information to the same `WINDANALYSIS` folder the user names in code.

For more details of analysis see the examples folder for a few examples using sample data in `WINDANALYSIS`.

You can optionally also export analysis tables and datasets to EXCEL and MATLAB compatible files. (ikr amazing)
