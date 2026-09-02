from models.WindAnalyser import WindAnalyser
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import correlate, correlation_lags, welch
from scipy.signal import welch, csd, detrend, find_peaks
from scipy import signal


def get_spectral_peaks(time, velocity, n_peaks=5):
    """
    Calculate the dominant spectral peaks and their relative amplitudes.

    Returns
    -------
    dict
        {frequency_hz: relative_amplitude}
    """

    time = np.asarray(time)
    velocity = np.asarray(velocity)

    # Remove invalid samples
    valid = np.isfinite(time) & np.isfinite(velocity)
    time = time[valid]
    velocity = velocity[valid]

    # Sampling frequency
    dt = np.median(np.diff(time))
    fs = 1.0 / dt

    # Remove mean velocity
    velocity = velocity - np.mean(velocity)

    # Calculate PSD
    frequencies, psd = welch(
        velocity,
        fs=fs,
        nperseg=min(len(velocity), int(fs * 10))
    )

    # Find local maxima
    peak_indices, _ = find_peaks(psd)

    if len(peak_indices) == 0:
        return {}

    # Sort by peak power
    peak_indices = peak_indices[
        np.argsort(psd[peak_indices])[::-1]
    ]

    # Take strongest peaks
    peak_indices = peak_indices[:n_peaks]

    # Use sqrt(PSD) as relative amplitude measure
    amplitudes = np.sqrt(psd[peak_indices])

    # Normalise using RMS-style magnitude
    amplitudes /= np.sqrt(np.sum(amplitudes**2))

    # Return frequency -> relative amplitude
    return {
        frequencies[i]: amplitude
        for i, amplitude in zip(peak_indices, amplitudes)
    }

experiment_name = "test_spectral"
df = WindAnalyser.load_experiment_dataset(experiment_name)
v_applied = 8
error_row = df.loc[df['applied velocity'] == v_applied].iloc[-1]
ti_applied = error_row['applied TI']/100

velocity = error_row['windspeed_z_list']
time = error_row['time_s_list']
print(max(time))
print(f"Velocity: {np.mean(velocity)} | Error = {(np.mean(velocity)-v_applied)/v_applied * 100:.2f} %")

ti = np.std(velocity)/np.mean(velocity)
print(f"TI: {ti * 100:.2f}% | Error = {(ti-ti_applied)/ti_applied * 100:.2f} %")
peaks = get_spectral_peaks(time, velocity, n_peaks=5)

for frequency, amplitude in peaks.items():
    print(f"{frequency:.3f} Hz -> {amplitude:.3f}")
plt.plot(time, velocity,'-')
plt.grid()
plt.show()



