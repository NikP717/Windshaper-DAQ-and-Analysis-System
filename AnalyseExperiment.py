from models.WindAnalyser import WindAnalyser
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import correlate, correlation_lags, welch
from scipy.signal import welch, csd, detrend

import regex as re


experiment_name = "208V_uniformflow_baseline_check"
df = WindAnalyser.load_experiment_dataset(experiment_name)
# frequencies = df['wind_fq']
# amplitudes = df['wind_amplitude']
# means = df['wind_avg']
# repeats = df['repeat']
# pwms = df['fan_pwm']
# velocity_lists = df['windspeed_z_list']
# pwm_lists = df['avg_pwm_list']
# rpm_lists = df['avg_rpm_list']
# time_lists = df['time_s_list']
# tis = df['TI_percent_z']
# velocity = df["mean_speed_mps_z"]
# pwm_instr = df['fan_pwm']
# rpm_lists = df['avg_rpm_list']
# rpm_std_lists = df['rpm_std_list']
# pwm_std_lists = df['pwm_std_list']

# analysis_df = pd.DataFrame(columns=["repeat","pwm","TI","Vz"])
# analysis_df['repeat'] = repeats
# analysis_df['pwm'] = pwms
# analysis_df['TI'] = tis
# analysis_df['Vz'] = velocity
# mean_analysis_df = WindAnalyser.average_dataset(analysis_df,None,groupby="pwm")
# WindAnalyser.save_analysis_dataset(mean_analysis_df,"Summary Statistics")

# i = 0
# for velocities,times,pwms, rep in zip(velocity_lists,time_lists,pwm_instr,repeats):
#     plt.figure()
#     plt.plot(times,velocities,'-',label=f"PWM {pwms}")
#     plt.xlabel("Time [s]")
#     plt.ylabel("Velocity [m/s]")
#     plt.legend()
#     plt.grid()
#     i+= 1
#     WindAnalyser.save_plot(f"Velocity Plot Test {i} repeat {rep}")
# i = 0
# for pwms,r,t,p,rep in zip(pwm_instr,rpm_lists,time_lists,pwm_lists,repeats):
#     plt.figure()
#     plt.plot(t,r,'x-',label=f"PWM {pwms}")
#     plt.plot(t,p,'x-',label=f"PWM {pwms}")
#     plt.grid()
#     plt.legend()
#     i+= 1
#     WindAnalyser.save_plot(f"PWM_RPM Plot Test {i} repeat {rep}")
#     plt.close()
# i = 0
# for r,p,time,pwms,rep in zip(rpm_std_lists,pwm_std_lists, time_lists, pwm_instr,repeats):
#     plt.figure()
#     min_rows = min(r.shape[0], t.shape[0])

#     # Slice both DataFrames to match
#     t_cut = t.iloc[:min_rows]
#     r_cut = r.iloc[:min_rows]
#     plt.plot(t_cut,r_cut,'x-',label=f"PWM {pwms}")
#     plt.ylabel("RPM Standard Deviation")
#     plt.xlabel("Time [s]")
#     plt.legend()
#     plt.grid()
#     i+= 1
#     WindAnalyser.save_plot(f"RPM_std Plot Test {i} repeat {rep}")
#     plt.close()

#     plt.figure()
#     min_rows = min(r.shape[0], t.shape[0])
#     # Slice both DataFrames to match
#     t_cut = t.iloc[:min_rows]
#     p_cut = p.iloc[:min_rows]
#     plt.plot(t_cut,p_cut,'x-',label=f"PWM {pwms}")
#     plt.ylabel("PWM Standard Deviation")
#     plt.xlabel("Time [s]")
#     plt.legend()
#     plt.grid()
#     WindAnalyser.save_plot(f"PWM_std Plot Test {i} repeat {rep}")
#     plt.close()
# WindAnalyser.plot_tool(mean_analysis_df,analysis_df,'pwm','Vz',"PWM Setting [%]","Mean Axial Velocity [m/s]",group_by='pwm',plot_raw_data=True,error_bars=True)
# WindAnalyser.plot_tool(mean_analysis_df,analysis_df,'pwm','Vz',"PWM Setting [%]","Mean Axial Velocity [m/s]",group_by='pwm',plot_raw_data=True,error_bars=True)

# WindAnalyser.save_analysis_dataset_matlab(mean_analysis_df,"test1")

# """
# DATA STRUCTURE
# ======================
# "time_s_list",
# "windspeed_x_list",
# "windspeed_y_list",
# "windspeed_z_list",
# "static_pressure_list",
# "temperature_celsius_list",
# "atmospheric_pressure_hPa_list",
# "avg_pwm_list",
# "avg_rpm_list",
# "avg_target_pwm_list",
# "pwm_std_list",
# "rpm_std_list",
# "fan_pwm",
# "upstream_pwm",
# "downstream_pwm",
# "distance_from_wall",
# "probe_pos_x",
# "probe_pos_y",
# "repeat",
# "wind_fq",
# "wind_amplitude",
# "wind_avg",
# "mean_speed_mps_x",
# "std_fluctuation_mps_x",
# "TI_percent_x",
# "rolling_mean_variation_x",
# "rolling_std_variation_x",
# "ADF_pvalue_x",
# "integral_time_scale_s_x",
# "integral_length_scale_m_x",
# "mean_speed_mps_y",
# "std_fluctuation_mps_y",
# "TI_percent_y",
# "rolling_mean_variation_y",
# "rolling_std_variation_y",
# "ADF_pvalue_y",
# "integral_time_scale_s_y",
# "integral_length_scale_m_y",
# "mean_speed_mps_z",
# "std_fluctuation_mps_z",
# "TI_percent_z",
# "rolling_mean_variation_z",
# "rolling_std_variation_z",
# "ADF_pvalue_z",
# "integral_time_scale_s_z",
# "integral_length_scale_m_z",
# "mean_speed_mps_3d",
# "std_fluctuation_mps_3d",
# "TI_percent_3d",
# "rolling_mean_variation_3d",
# "rolling_std_variation_3d",
# "ADF_pvalue_3d",
# "integral_time_scale_s_3d",
# "integral_length_scale_m_3d"
# # """
# experiment_name = "208V_sinewave_baseline_check"
# df = WindAnalyser.load_experiment_dataset(experiment_name)
# frequencies = df['wind_fq']
# amplitudes = df['wind_amplitude']
# means = df['wind_avg']
# repeats = df['repeat']
# velocity_lists = df['windspeed_z_list']
# pwm_lists = df['avg_pwm_list']
# rpm_lists = df['avg_rpm_list']
# time_lists = df['time_s_list']
# tis = df['TI_percent_z']

# def sine_fit_known_frequency(t, x, f_hz):
#     """
#     Fit x(t) = C + A sin(2*pi*f*t + phi)
 
#     This uses a linear least-squares form:
#     x(t) = C + Bsin sin(wt) + Bcos cos(wt)
 
#     Then:
#     A = sqrt(Bsin^2 + Bcos^2)
#     phi = atan2(Bcos, Bsin)
#     """
#     t = np.asarray(t, dtype=float)
#     x = np.asarray(x, dtype=float)
 
#     omega = 2 * np.pi * f_hz
 
#     X = np.column_stack([
#         np.ones_like(t),
#         np.sin(omega * t),
#         np.cos(omega * t)
#     ])
 
#     coef, *_ = np.linalg.lstsq(X, x, rcond=None)
 
#     C = coef[0]
#     Bsin = coef[1]
#     Bcos = coef[2]
 
#     A = np.sqrt(Bsin**2 + Bcos**2)
#     phi = np.arctan2(Bcos, Bsin)
 
#     x_fit = C + A * np.sin(omega * t + phi)
 
#     residual = x - x_fit
#     residual_rms = np.sqrt(np.mean(residual**2))
 
#     ss_res = np.sum(residual**2)
#     ss_tot = np.sum((x - np.mean(x))**2)
#     r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
 
#     return (C, A, phi, np.degrees(phi), x_fit, residual_rms, r2)

# def wrap_to_pi(angle):
#     """Wrap angle to [-pi, pi]."""
#     return (angle + np.pi) % (2 * np.pi) - np.pi

# def phase_lag_relative_to_pwm(signal_phase, pwm_phase, f_hz):
#     """
#     Compute phase and time lag of a signal relative to PWM.
 
#     Positive time lag means the signal response occurs AFTER the PWM command.
#     """
#     phase_diff_rad = signal_phase - pwm_phase
#     omega = 2 * np.pi * f_hz
#     phase_diff_rad_unwrapped = np.unwrap([0, phase_diff_rad])[1]
#     lag_s = -phase_diff_rad_unwrapped / omega 

#     phase_diff_rad = wrap_to_pi(phase_diff_rad)
#     phase_diff_deg = np.degrees(phase_diff_rad)

#     return phase_diff_rad, phase_diff_deg, lag_s

# def compute_psd(t, x):
#     t = np.asarray(t, dtype=float)
#     x = np.asarray(x, dtype=float)
 
#     dt = np.median(np.diff(t))
#     fs_hz = 1.0 / dt
 
#     x_fluc = x - np.mean(x)
 
#     nperseg = min(4096, len(x_fluc))
#     nperseg = max(256, nperseg)
 
#     f, Pxx = welch(x_fluc, fs=fs_hz, nperseg=nperseg, detrend="constant")
 
#     return f, Pxx, fs_hz
 
# def find_psd_peak_near_frequency(f, Pxx, target_f):
#     """
#     Find PSD peak near imposed frequency.
#     """
#     band_width = max(0.05, 0.25 * target_f)
#     mask = (f >= target_f - band_width) & (f <= target_f + band_width)
 
#     if not np.any(mask):
#         return np.nan, np.nan
 
#     f_band = f[mask]
#     P_band = Pxx[mask]
 
#     idx = np.argmax(P_band)
 
#     return f_band[idx], P_band[idx]

# def crosscorr_lag_limited(t, command, response, input_f):
#     import numpy as np
#     from scipy.signal import correlate, correlation_lags
 
#     dt = np.median(np.diff(t))
#     fs = 1 / dt
 
#     x = command - np.mean(command)
#     y = response - np.mean(response)
 
#     x = x / np.std(x)
#     y = y / np.std(y)
 
#     corr = correlate(y, x, mode="full")
#     lags = correlation_lags(len(y), len(x), mode="full")
#     lag_s = lags / fs
 
#     max_lag_s = 0.5 / input_f  # half period
#     keep = np.abs(lag_s) <= max_lag_s
 
#     lag_s = lag_s[keep]
#     corr = corr[keep]
 
#     i = np.argmax(corr)

#     return lag_s[i], corr[i]

# def calculate_frf_coherence(
#     time,
#     pwm,
#     response,
#     input_frequency,
#     cycles_per_segment=4,
#     overlap_fraction=0.5,
# ):
#     """
#     Calculate PWM-to-response FRF and magnitude-squared coherence.
 
#     Parameters
#     ----------
#     time : array
#         Common time vector in seconds.
#     pwm : array
#         Raw PWM time series in percent.
#     response : array
#         Raw RPM or velocity time series.
#     input_frequency : float
#         Imposed sinusoidal frequency in Hz.
#     cycles_per_segment : int
#         Number of forcing cycles in each Welch segment.
#     overlap_fraction : float
#         Welch segment overlap fraction.
 
#     Returns
#     -------
#     result : dict
#         Gain, phase, coherence and equivalent phase delay at input frequency.
#     spectra : dict
#         Full frequency-dependent spectra for plotting.
#     """
 
#     time = np.asarray(time, dtype=float)
#     pwm = np.asarray(pwm, dtype=float)
#     response = np.asarray(response, dtype=float)
 
#     valid = (
#         np.isfinite(time)
# & np.isfinite(pwm)
# & np.isfinite(response)
#     )
 
#     time = time[valid]
#     pwm = pwm[valid]
#     response = response[valid]
 
#     order = np.argsort(time)
#     time = time[order]
#     pwm = pwm[order]
#     response = response[order]
 
#     # Estimate sampling frequency
#     dt = np.median(np.diff(time))
#     fs = 1.0 / dt
 
#     # Resample to an exactly uniform time grid
#     uniform_time = np.arange(time[0], time[-1], dt)
#     pwm_uniform = np.interp(uniform_time, time, pwm)
#     response_uniform = np.interp(uniform_time, time, response)
 
#     # Remove mean values; do not use IQR normalization for FRF
#     x = detrend(pwm_uniform, type="constant")
#     y = detrend(response_uniform, type="constant")
 
#     # Segment containing the requested number of forcing cycles
#     segment_duration = cycles_per_segment / input_frequency
#     nperseg = int(round(segment_duration * fs))
#     nperseg = min(nperseg, len(x))
 
#     noverlap = int(round(overlap_fraction * nperseg))
#     noverlap = min(noverlap, nperseg - 1)
 
#     step = nperseg - noverlap
#     number_of_segments = 1 + max(0, (len(x) - nperseg) // step)
 
#     if number_of_segments < 4:
#         print(
#             f"Warning: only {number_of_segments} Welch segments. "
#             "Coherence uncertainty may be large."
#         )
 
#     spectral_options = dict(
#         fs=fs,
#         window="hann",
#         nperseg=nperseg,
#         noverlap=noverlap,
#         detrend=False,
#         scaling="density",
#     )
 
#     frequency, Sxx = welch(x, **spectral_options)
#     _, Syy = welch(y, **spectral_options)
#     _, Sxy = csd(x, y, **spectral_options)
 
#     # H1 transfer-function estimator: response / PWM
#     small = np.finfo(float).eps
#     H1 = Sxy / np.maximum(Sxx, small)
 
#     coherence = (
#         np.abs(Sxy) ** 2
#         / np.maximum(Sxx * Syy, small)
#     )
#     coherence = np.clip(coherence, 0.0, 1.0)
 
#     # Value at nearest spectral bin to imposed frequency
#     index = np.argmin(np.abs(frequency - input_frequency))
 
#     gain_linear = np.abs(H1[index])
#     phase_deg_wrapped = np.angle(H1[index], deg=True)
#     coherence_at_input = coherence[index]
 
#     equivalent_delay = (
#         -phase_deg_wrapped
#         / (360.0 * input_frequency)
#     )
 
#     result = {
#         "input_frequency_hz": input_frequency,
#         "spectral_frequency_hz": frequency[index],
#         "gain_linear": gain_linear,
#         "phase_deg_wrapped": phase_deg_wrapped,
#         "equivalent_delay_s_wrapped": equivalent_delay,
#         "coherence": coherence_at_input,
#         "number_of_welch_segments": number_of_segments,
#         "sampling_frequency_hz": fs,
#     }
 
#     spectra = {
#         "frequency_hz": frequency,
#         "H1": H1,
#         "gain": np.abs(H1),
#         "phase_deg": np.angle(H1, deg=True),
#         "coherence": coherence,
#         "Sxx": Sxx,
#         "Syy": Syy,
#         "Sxy": Sxy,
#     }
 
#     return result, spectra

# analysis_table = pd.DataFrame(columns=['v_frf_fq','v_frf_gain','v_frf_phase_deg','v_coherence','r_frf_fq','r_frf_gain','r_frf_phase_deg','r_coherence','repeat','TI_vz','TI_sine','TI_residual','TI_total','raw_rpm_list','raw_pwm_list','raw_v_list','t_list','input_f','input_amp','input_mean','pwm_f','pwm_amp','pwm_mean','pwm_phase_rad','pwm_phase_deg','pwm_fit','pwm_residual','pwm_r2','v_amplitude','v_mean','v_phase_rad','v_phase_deg','v_fit','v_residual','v_r2','v_phase_diff_rad','v_phase_diff_deg','v_lag_time_s','r_amplitude','r_mean','r_phase_rad','r_phase_deg','r_fit','r_residual','r_r2','r_phase_diff_rad','r_phase_diff_deg','r_lag_time_s','v_f_band','v_p_band','v_lag_calc'])
# for TI,f,a,m,v,pwm,rpm,t,r in zip(tis,frequencies,amplitudes,means,velocity_lists,pwm_lists,rpm_lists,time_lists,repeats):
#     velocity_sine = sine_fit_known_frequency(t, v, f)
#     pwm_sine = sine_fit_known_frequency(t, pwm, f)
#     rpm_sine = sine_fit_known_frequency(t, rpm, f)
#     v_mean,v_amp,v_phase_rad,v_phase_deg,v_fit,v_residual,v_r2 = velocity_sine
#     p_mean,p_amp,p_phase_rad,p_phase_deg,p_fit,p_residual,p_r2 = pwm_sine
#     r_mean,r_amp,r_phase_rad,r_phase_deg,r_fit,r_residual,r_r2 = rpm_sine
#     v_phase_diff_rad, v_phase_diff_deg, v_lag_time_s = phase_lag_relative_to_pwm(v_phase_rad,p_phase_rad,f)
#     r_phase_diff_rad, r_phase_diff_deg, r_lag_time_s = phase_lag_relative_to_pwm(r_phase_rad,p_phase_rad,f)
#     TI_sine = (v_amp / np.sqrt(2)) / v_mean * 100
#     residual = v - v_fit
#     TI_residual = np.std(residual, ddof=1) / v_mean * 100
#     TI_total = np.sqrt(TI_sine**2 + TI_residual**2)
#     v_psd_f,v_psd_pxx, _ = compute_psd(t,v)
#     v_f_band, v_P_band = find_psd_peak_near_frequency(v_psd_f,v_psd_pxx,f)
#     v_lag_calc, _ = crosscorr_lag_limited(t,pwm,v,f)
#     #FRF CALCS
#     v_result, v_spectra = calculate_frf_coherence(t,pwm,v,f)
#     r_result, r_spectra = calculate_frf_coherence(t,pwm,rpm,f)
#     v_frf_fq = v_result["spectral_frequency_hz"]
#     v_frf_gain = v_result["gain_linear"]
#     v_frf_phase_deg = v_result["phase_deg_wrapped"]
#     v_coherence = v_result['coherence']

#     r_frf_fq = r_result["spectral_frequency_hz"]
#     r_frf_gain = r_result["gain_linear"]
#     r_frf_phase_deg = r_result["phase_deg_wrapped"]
#     r_coherence = r_result['coherence']

#     analysis_table = WindAnalyser.add_data_row(analysis_table,[v_frf_fq,v_frf_gain,v_frf_phase_deg,v_coherence,r_frf_fq,r_frf_gain,r_frf_phase_deg,r_coherence, r,TI,TI_sine,TI_residual,TI_total,rpm,pwm,v,t,f,a,m,f,p_amp,p_mean,p_phase_rad,p_phase_deg,p_fit,p_residual,p_r2,v_amp,v_mean,v_phase_rad,v_phase_deg,v_fit,v_residual,v_r2,v_phase_diff_rad,v_phase_diff_deg,v_lag_time_s,r_amp,r_mean,r_phase_rad,r_phase_deg,r_fit,r_residual,r_r2,r_phase_diff_rad,r_phase_diff_deg,r_lag_time_s,v_f_band,v_P_band,v_lag_calc])

# # physical gain
# velocity_gains = (analysis_table['v_amplitude'].to_numpy(dtype=float)/analysis_table['pwm_amp'].to_numpy(dtype=float))
# analysis_table['v_gain'] = velocity_gains

# rpm_gains = (analysis_table['r_amplitude'].to_numpy(dtype=float)/analysis_table['pwm_amp'].to_numpy(dtype=float))
# analysis_table['r_gain'] = rpm_gains

# # turbulence comparison
# turbulence_trust = analysis_table['TI_sine'] - analysis_table['TI_residual']
# analysis_table['TI_check'] = turbulence_trust

# WindAnalyser.save_analysis_dataset(analysis_table,"Calculated Quantities")
# mean_analysis_table = WindAnalyser.average_dataset(analysis_table,['p_phase_deg','v_phase_deg','r_phase_deg','v_phase_diff_deg','r_phase_diff_deg'],['input_amp','input_mean','input_f']) # WARNING, ONLY WRAPS ANGLES SPECIFIED
# # clean_dataset, mean_analysis_table, outlier_dataset = WindAnalyser.seperate_dataset_outliers(mean_analysis_table,analysis_table,)


# #FRFs
# FRF_v_gains = analysis_table['v_frf_gain'].astype(float)
# FRF_r_gains = analysis_table['r_frf_gain'].astype(float)
# analysis_table['v_frf_gain_DB_norm'] = 20*np.log10(FRF_v_gains / mean_analysis_table['v_frf_gain'].iloc[0])
# mean_analysis_table['v_frf_gain_DB_norm'] = 20*np.log10(mean_analysis_table['v_frf_gain'] / mean_analysis_table['v_frf_gain'].iloc[0])

# analysis_table['r_frf_gain_DB_norm'] = 20*np.log10(FRF_r_gains / mean_analysis_table['r_frf_gain'].iloc[0])
# mean_analysis_table['r_frf_gain_DB_norm'] = 20*np.log10(mean_analysis_table['r_frf_gain'] / mean_analysis_table['r_frf_gain'].iloc[0])

# for phase_col in ['v_phase_diff_deg', 'r_phase_diff_deg','v_frf_phase_deg','r_frf_phase_deg']:
#     rad = np.deg2rad(mean_analysis_table[phase_col])
#     unwrapped_rad = np.unwrap(rad)
#     mean_analysis_table[phase_col] = np.rad2deg(unwrapped_rad)
#     col = analysis_table[phase_col].to_numpy(dtype=float)
#     col = np.deg2rad(col)
#     unwrapped_rad = np.unwrap(col)
#     analysis_table[phase_col] = np.rad2deg(unwrapped_rad)

# WindAnalyser.save_analysis_dataset(mean_analysis_table[['input_f','input_amp','input_mean','v_amplitude','v_mean','v_frf_fq','v_frf_gain','v_frf_phase_deg','r_frf_fq','r_frf_gain','r_frf_phase_deg','TI_sine','TI_residual','TI_total']],"Calculated Mean Quantities")

# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','v_phase_diff_deg',"Input PWM Frequency (Hz)","Velocity Phase Lag [deg].", group_by='input_amp',error_bars=True,plot_raw_data=True)
# fig, ax = WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','v_lag_time_s',"Input PWM Frequency (Hz)","Velocity Time Lag [s].", group_by='input_amp',save=False,error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','v_lag_calc',"Input PWM Frequency (Hz)","Velocity Time Lag [s].",group_by="input_amp",ax=ax)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','v_gain',"Input PWM Frequency (Hz)","Velocity Gain from PWM [m/s/PWM%].", group_by='input_amp',error_bars=True,plot_raw_data=True)

# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','r_phase_diff_deg',"Input PWM Frequency (Hz)","RPM Phase Lag [deg].", group_by='input_amp',error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','r_lag_time_s',"Input PWM Frequency (Hz)","RPM Time Lag [s].", group_by='input_amp',save=False,error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','r_gain',"Input PWM Frequency (Hz)","RPM Gain from PWM  [RPMPWM%].", group_by='input_amp',error_bars=True,plot_raw_data=True)

# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','TI_vz',"Input PWM Frequency (Hz)","Turbulence Intensity (z) (%)",group_by='input_amp',error_bars=True,plot_raw_data=True)
# # WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_amp','TI_vz',"Input PWM Amplitude (%)","Turbulence Intensity (z) (%)",group_by='input_f',error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','TI_sine',"Input PWM Frequency (Hz)","Coherent Gust Intensity (%)",group_by='input_amp',error_bars=True,plot_raw_data=True)
# # WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_amp','TI_sine',"Input PWM Amplitude (%)","Coherent Gust Intensity (%)",group_by='input_f',error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','TI_residual',"Input PWM Frequency (Hz)","Residual Turbulence Intensity (%)",group_by='input_amp',error_bars=True,plot_raw_data=True)
# # WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_amp','TI_residual',"Input PWM Amplitude (%)","Residual Turbulence Intensity (%)",group_by='input_f',error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','TI_total',"Input PWM Frequency (Hz)","Total Fluctuation Intensity (%)",error_bars=True,plot_raw_data=True)

# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','v_frf_gain',"Input PWM Frequency (Hz)","FRF Velocity Gain",error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','r_frf_gain',"Input PWM Frequency (Hz)","FRF RPM Gain",error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','v_frf_phase_deg',"Input PWM Frequency (Hz)","FRF Velocity Phase",error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','r_frf_phase_deg',"Input PWM Frequency (Hz)","FRF RPM Phase",error_bars=True,plot_raw_data=True)

# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','v_coherence',"Input PWM Frequency (Hz)","FRF Velocity Coherence",error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','r_coherence',"Input PWM Frequency (Hz)","FRF RPM Coherence",error_bars=True,plot_raw_data=True)


# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','v_frf_gain_DB_norm',"Input PWM Frequency (Hz)","Normalised FRF Velocity Gain (dB)",error_bars=True,plot_raw_data=True)
# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','r_frf_gain_DB_norm',"Input PWM Frequency (Hz)","Normalised FRF RPM Gain (dB)",error_bars=True,plot_raw_data=True)

# WindAnalyser.plot_tool(mean_analysis_table,analysis_table,'input_f','TI_check',"Input PWM Frequency (Hz)","Coherent - Residual Turbulence Intensity [%]",group_by='input_amp',error_bars=True,plot_raw_data=True)

# # # CONFIRM RELATIONS

# def normalize_for_plot(x):
#     # USING INTERQUARTILE RANGE DUE TO NOISE
#     x = np.asarray(x)
#     x0 = x - np.nanmedian(x)  # Median is tougher against outliers than mean
#     q75, q25 = np.nanpercentile(x0, [75, 25])
#     denom = q75 - q25
#     if denom == 0:
#         return x0
#     return x0 / denom
# start_time = 20
# plt.figure()
# print(len(frequencies))
# iloc_num = 0
# plt.title(f"MetaData: INPUT FQ: {analysis_table['input_f'][iloc_num]:.2f} Hz, INPUT AMP: {analysis_table['input_amp'][iloc_num]:.2f}%, INPUT MEAN {analysis_table['input_mean'][iloc_num]:.2f}%")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_v_list'].iloc[iloc_num]),label="Velocity",alpha=0.5)
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['v_fit'].iloc[iloc_num]),label="Velocity Fit")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_rpm_list'].iloc[iloc_num]),label="RPM")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['r_fit'].iloc[iloc_num]),label="RPM Fit")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_pwm_list'].iloc[iloc_num]),label="PWM")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['pwm_fit'].iloc[iloc_num]),label="PWM Fit")
# plt.xlabel("Time [s]")
# plt.ylabel("Normalised by IQR Amplitude [-]")
# plt.xlim(start_time,start_time + 2/analysis_table['input_f'][iloc_num])
# plt.grid()
# plt.legend()
# WindAnalyser.save_plot("Normalised Sine Plot 1")
# plt.figure()
# iloc_num = 3
# plt.title(f"MetaData: INPUT FQ: {analysis_table['input_f'][iloc_num]:.2f} Hz, INPUT AMP: {analysis_table['input_amp'][iloc_num]:.2f}%, INPUT MEAN {analysis_table['input_mean'][iloc_num]:.2f}%")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_v_list'].iloc[iloc_num]),label="Velocity",alpha=0.5)
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['v_fit'].iloc[iloc_num]),label="Velocity Fit")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_rpm_list'].iloc[iloc_num]),label="RPM")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['r_fit'].iloc[iloc_num]),label="RPM Fit")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_pwm_list'].iloc[iloc_num]),label="PWM")
# plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['pwm_fit'].iloc[iloc_num]),label="PWM Fit")
# plt.xlabel("Time [s]")
# plt.ylabel("Normalised by IQR Amplitude [-]")
# plt.xlim(start_time,start_time + 2/analysis_table['input_f'][iloc_num])
# plt.grid()
# plt.legend()
# WindAnalyser.save_plot("Normalised Sine Plot 2")

# # # plt.figure()
# # # iloc_num = 59
# # # plt.title(f"MetaData: INPUT FQ: {analysis_table['input_f'][iloc_num]:.2f} Hz, INPUT AMP: {analysis_table['input_amp'][iloc_num]:.2f}%, INPUT MEAN {analysis_table['input_mean'][iloc_num]:.2f}%")
# # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_v_list'].iloc[iloc_num]),label="Velocity",alpha=0.5)
# # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['v_fit'].iloc[iloc_num]),label="Velocity Fit")
# # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_rpm_list'].iloc[iloc_num]),label="RPM")
# # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['r_fit'].iloc[iloc_num]),label="RPM Fit")
# # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_pwm_list'].iloc[iloc_num]),label="PWM")
# # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['pwm_fit'].iloc[iloc_num]),label="PWM Fit")
# # # plt.xlabel("Time [s]")
# # # plt.ylabel("Normalised by Maximum Amplitude [-]")
# # # plt.xlim(start_time,start_time + 2/analysis_table['input_f'][iloc_num])
# # # plt.grid()
# # # plt.legend()
# # # WindAnalyser.save_plot("Normalised Sine Plot 3")


# # # plt.figure()
# # # iloc_num = 28
# # # plt.title(f"MetaData: INPUT FQ: {analysis_table['input_f'][iloc_num]:.2f} Hz, INPUT AMP: {analysis_table['input_amp'][iloc_num]:.2f}%, INPUT MEAN {analysis_table['input_mean'][iloc_num]:.2f}%")
# # # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_v_list'].iloc[iloc_num]),label="Velocity",alpha=0.5)
# # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['v_fit'].iloc[iloc_num]),label="Velocity Fit")
# # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_pwm_list'].iloc[iloc_num]),label="PWM")
# # # plt.plot(analysis_table['t_list'].iloc[iloc_num],normalize_for_plot(analysis_table['raw_rpm_list'].iloc[iloc_num]),label="RPM")

# # # plt.xlabel("Time [s]")
# # # plt.ylabel("Normalised by Maximum Amplitude [-]")
# # # plt.legend()
# # # WindAnalyser.save_plot("Normalised Check Plot")
# # # time = convert_pd_column_to_np(df, 'time_s_list')
# # # wind_speed_z = convert_pd_column_to_np(df, 'windspeed_z_list')
# # # pwms = convert_pd_column_to_np(df, 'avg_pwm_list')
# # # rpms = convert_pd_column_to_np(df, 'avg_rpm_list')
# # # print(df['mean_speed_mps_z'].iloc[0])

# # # def sine_normalise(quantity):
# # #     return 2 * (quantity-quantity.min())/(quantity.max()-quantity.min()) - 1

# # # norm_v = sine_normalise(wind_speed_z)
# # # norm_pwm = sine_normalise(pwms)
# # # norm_rpm = sine_normalise(rpms)
# # # plt.figure()
# # # plt.xlabel("Time [s]")
# # # plt.ylabel("Normalised Magnitude [-]")
# # # # plt.plot(time,norm_pwm,'b-',label="Normalised PWM")
# # # plt.plot(time,norm_v,'r-',label="Normalised Velocity",alpha=0.5)
# # # plt.plot(time,norm_rpm,'g-',label="Normalised RPM")
# # # plt.grid()
# # # plt.legend()
# # # plt.show()