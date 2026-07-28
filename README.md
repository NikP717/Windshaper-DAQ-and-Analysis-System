# Credits
Nicholas Pedzik 17/07/2026
`windprobe_api` WindProbe API: Copyright (C)2018-2022 WindShape Ltd - All Rights Reserved, Old Probe API 

# Dependencies
The scripts requires `Astral uv` to manage the libraries and run the scripts. 

You can install it on every system using [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

With this package, upon running this directory all necessary libraries will be installed automatically.

This script uses a Series X WindShape windprobe and will not work for newer Series A probes (TO BE UPDATED TO WORK FOR BOTH)

# Zeroing

The zeroing of the pressure sensors is done when you plug the WindProbe to your computer.

# USB

The probe needs to be directly connected to the computer, not through a USB hub.

## How to run

Open a terminal in this directory and enter `uv run python -i configure_experiment.py`

You may run any configuration file of your choice however this is the default, see examples for how to create your own experiment configurations.

# Examples

Examples can be found in the examples folder, in order to try these, please move or create a python file in the main folder (not the examples subfolder) in order for the run command to work.

# How to Operate

This script requires a direct USB connection to the Probe AND a direct LAN connection to the WindShaper, LAN adapters also work here.

For configurations, review examples for available profiles or directly view available functions within the `models.WindController` file.

Once the flow profile begins the data logging begins, same applies when it ends.

## Data Handling and formatting

This script automatically deposists single configuration data from an experiment to an excel file in `WINDDATA`.

If you force a save experiment at the end of running a series of configurations, all `WINDDATA` files are moved and converted to an experiment folder in `WINDANALYSIS`.

These two processes follow a structured formatting:
Dataframes in `WINDDATA` have a row for each sample.
Dataframes in `WINDANALYSIS` have a row for each configuration (series of samples).

# ExperimentSeriesDataSet Structure
**Columns:**
"time_s_list",
"windspeed_x_list",
"windspeed_y_list",
"windspeed_z_list",
"static_pressure_list",
"temperature_celsius_list",
"atmospheric_pressure_hPa_list",
"avg_pwm_list",
"avg_rpm_list",
"avg_target_pwm_list",
"pwm_std_list",
"rpm_std_list",
"fan_pwm",
"upstream_pwm",
"downstream_pwm",
"distance_from_wall",
"probe_pos_x",
"probe_pos_y",
"repeat",
"wind_fq",
"wind_amplitude",
"wind_avg",
"mean_speed_mps_x",
"std_fluctuation_mps_x",
"TI_percent_x",
"rolling_mean_variation_x",
"rolling_std_variation_x",
"ADF_pvalue_x",
"integral_time_scale_s_x",
"integral_length_scale_m_x",
"mean_speed_mps_y",
"std_fluctuation_mps_y",
"TI_percent_y",
"rolling_mean_variation_y",
"rolling_std_variation_y",
"ADF_pvalue_y",
"integral_time_scale_s_y",
"integral_length_scale_m_y",
"mean_speed_mps_z",
"std_fluctuation_mps_z",
"TI_percent_z",
"rolling_mean_variation_z",
"rolling_std_variation_z",
"ADF_pvalue_z",
"integral_time_scale_s_z",
"integral_length_scale_m_z",
"mean_speed_mps_3d",
"std_fluctuation_mps_3d",
"TI_percent_3d",
"rolling_mean_variation_3d",
"rolling_std_variation_3d",
"ADF_pvalue_3d",
"integral_time_scale_s_3d",
"integral_length_scale_m_3d"

I know right quite the mouthful, but plenty of flexibility for anaylsis with all these variables.

# Quantities

This script automatically calculates the following quantities and attaches it to raw probe data: 
Mean Velocity **[m/s]** , Velocity Standard Deviation **[m/s]** , Turbulence Intensity **[%]** , 
Rolling Mean and Standard deviation (statistical), Integral Time Scale **[s]** , Integral Length Scale  **[m]**
---------------------------------------------------
Raw Probe Data takes on the following form:
Time **[s]**, Ux **[m/s]**, Uy  **[m/s]**, Uz  **[m/s]**, pstat  **[Pa]**, Temperature **[°C]**, Atmospheric pressure **[hPa]**

Attached beside the Raw Probe Data is the live windshaper statistics
Average PWM **[%]**, Average RPM **[%]**, Average Target PWM **[%]**, PWM Standard Deviation **[%]**, RPM Standard Deviation **[%]**

These form the columns in individual `WINDDATA` instances.
---------------------------------------------------

## Data Analysis

This script also simplifies and enables the user to load experimental datasets once they have been saved with ease for analysis.

Any function which saves plots or exports tables is automatically depositing this information to the same `WINDANALYSIS` folder the user names in code.

For more details of analysis see the examples folder for a few examples using sample data in `WINDANALYSIS`.

You can optionally also export analysis tables and datasets to EXCEL and MATLAB compatible files. (ikr amazing)
