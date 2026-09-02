from models.WindAnalyser import WindAnalyser
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import correlate, correlation_lags, welch
from scipy.signal import welch, csd, detrend, find_peaks
from scipy import signal

"""This baseline script is an example analysis of the existing baseline ConfigureExperiment series.
NOTE: Analysis in this repository is extremely untested and has limited features, something to develop if youre looking for better analysis."""

name = "Baseline_experiment"
dataframe = WindAnalyser.load_experiment_dataset(name) # loads dataframe from WINDANALYSIS experiment name
print(f"Columns: {WindAnalyser.show_dataset_columns(dataframe)}")
print(f"Summary: {WindAnalyser.show_dataset_summary(dataframe)}")

averaged_dataframe = WindAnalyser.average_dataset(dataframe, groupby="PWM") # combines repeats by adding _mean and _std columns
print(f"Columns: {WindAnalyser.show_dataset_columns(averaged_dataframe)}")
print(f"Summary: {WindAnalyser.show_dataset_summary(averaged_dataframe)}")
print(averaged_dataframe['PWM'])


mean_velocities = averaged_dataframe['mean_speed_mps_z'] # change x,y,z depending on which axis you measured
turbulence_intensities = averaged_dataframe['TI_percent_z'] # change x,y,z depending on which axis you measured
pwms = averaged_dataframe['PWM'] # from custom metadata set

# can use windanalyser plot tool or create own plots and save automatically to WINDANALYSIS directory
WindAnalyser.plot_tool(averaged_dataframe, dataframe, 'PWM', 'mean_speed_mps_z', xlabel="PWM (%)", ylabel="Velocity (m/s)",plot_raw_data=True,error_bars=True,save=True)

# WindAnalyser allows you to easily save Pyplot plots automatically to WINDANALYSIS directory needed
plt.figure(1)
plt.plot(pwms, turbulence_intensities, 'x-')
plt.xlabel("PWM (%)")
plt.ylabel("Turbulence Intensity (%)")
plt.grid()
WindAnalyser.save_plot("Turbulence Plot")

WindAnalyser.save_analysis_dataset_matlab(averaged_dataframe, "MATLAB_Dataframe_version") # can save dataframes to matlab format too
