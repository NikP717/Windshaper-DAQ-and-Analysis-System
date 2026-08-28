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



# def compare_velocity_series(t1, v1, t2, v2, pos1, pos2, nperseg=1024, coherence_threshold=0.8):

#     t1 = np.asarray(t1, dtype=float).flatten()
#     v1 = np.asarray(v1, dtype=float).flatten()
#     t2 = np.asarray(t2, dtype=float).flatten()
#     v2 = np.asarray(v2, dtype=float).flatten()

#     n1 = min(len(t1), len(v1))
#     n2 = min(len(t2), len(v2))

#     t1, v1 = t1[:n1], v1[:n1]
#     t2, v2 = t2[:n2], v2[:n2]

#     mask1 = np.isfinite(t1) & np.isfinite(v1)
#     mask2 = np.isfinite(t2) & np.isfinite(v2)

#     t1, v1 = t1[mask1], v1[mask1]
#     t2, v2 = t2[mask2], v2[mask2]

#     start = max(t1.min(), t2.min())
#     end = min(t1.max(), t2.max())

#     if end <= start:
#         raise ValueError("No overlapping time region")

#     dt = max(np.median(np.diff(t1)), np.median(np.diff(t2)))
#     fs = 1 / dt

#     t = np.arange(start, end, dt)

#     v1_sync = np.interp(t, t1, v1)
#     v2_sync = np.interp(t, t2, v2)

#     raw_v1 = v1_sync.copy()
#     raw_v2 = v2_sync.copy()

#     v1_sync -= np.mean(v1_sync)
#     v2_sync -= np.mean(v2_sync)

#     corr = signal.correlate(v1_sync, v2_sync, mode="full")
#     corr /= np.std(v1_sync) * np.std(v2_sync) * len(v1_sync)

#     lags = signal.correlation_lags(
#         len(v1_sync),
#         len(v2_sync),
#         mode="full"
#     ) * dt

#     peak_idx = np.argmax(np.abs(corr))

#     f, coherence = signal.coherence(
#         v1_sync,
#         v2_sync,
#         fs=fs,
#         nperseg=min(nperseg, len(v1_sync))
#     )

#     _, csd = signal.csd(
#         v1_sync,
#         v2_sync,
#         fs=fs,
#         nperseg=min(nperseg, len(v1_sync))
#     )

#     phase = np.angle(csd)

#     valid = coherence >= coherence_threshold

#     return {
#         "time": t,
#         "raw_signal_1": raw_v1,
#         "raw_signal_2": raw_v2,
#         "signal_1": v1_sync,
#         "signal_2": v2_sync,
#         "cross_correlation": corr,
#         "lags": lags,
#         "peak_correlation": corr[peak_idx],
#         "peak_lag": lags[peak_idx],
#         "frequency": f,
#         "coherence": coherence,
#         "phase": phase,
#         "valid_coherence_frequency": f[valid],
#         "sampling_frequency": fs,
#         "pos_1":pos1,
#         "pos_2":pos2
#     }

# def plot_velocity_comparison(results):

#     fig, axs = plt.subplots(3, 1, figsize=(10, 10))

#     # Signals
#     pos_1 = results["pos_1"]
#     pos_2 = results["pos_2"]
#     axs[0].plot(results["time"], results["signal_1"], label=f"Pos: {pos_1}")
#     axs[0].plot(results["time"], results["signal_2"], label=f"Pos: {pos_2}")
#     axs[0].set_xlabel("Time (s)")
#     axs[0].set_ylabel("Velocity fluctuation")
#     axs[0].set_title("Synchronised Velocity Signals")
#     axs[0].legend()
#     axs[0].grid()

#     # Cross correlation
#     axs[1].plot(results["lags"], results["cross_correlation"])
#     axs[1].axvline(
#         results["peak_lag"],
#         linestyle="--",
#         label=f"Lag = {results['peak_lag']:.4f}s"
#     )
#     axs[1].set_xlabel("Lag (s)")
#     axs[1].set_ylabel("Cross-correlation")
#     axs[1].set_title(
#         f"Cross Correlation (Peak = {results['peak_correlation']:.3f})"
#     )
#     axs[1].legend()
#     axs[1].grid()

#     # Coherence
#     axs[2].plot(
#         results["frequency"],
#         results["coherence"]
#     )
#     axs[2].axhline(
#         0.8,
#         linestyle="--",
#         label="Coherence threshold"
#     )
#     axs[2].set_xlabel("Frequency (Hz)")
#     axs[2].set_ylabel(r"$\gamma^2$")
#     axs[2].set_title("Magnitude Squared Coherence")
#     axs[2].set_ylim(0,1)
#     axs[2].legend()
#     axs[2].grid()

#     plt.tight_layout()
#     WindAnalyser.save_plot("Velocity Comparison Plot")

# def plot_phase(results):

#     plt.figure(figsize=(10,4))

#     plt.plot(
#         results["frequency"],
#         np.unwrap(results["phase"])
#     )

#     plt.xlabel("Frequency (Hz)")
#     plt.ylabel("Phase (rad)")
#     plt.title("Cross Spectral Phase Difference")
#     plt.grid()
#     WindAnalyser.save_plot("Phase Plot")
#     plt.show()

# experiment_name = "Prelim_Spatial_Test"
# df = WindAnalyser.load_experiment_dataset(experiment_name)
# df = df.drop(df.index[-1]) # drop final experiment, not needed rn
# _df = df[df['probe_pos_y'] == 16]
# _df2 = df[df['probe_pos_y'] == 24]
# u1 = _df['windspeed_z_list'].to_list()

# u2 = _df2['windspeed_z_list'].to_list()
# time_series_1 = _df['time_s_list'].to_list()
# time_series_2 = _df['time_s_list'].to_list()
# p1 = (16,16)
# p2 = (16,24)
# results_dict = compare_velocity_series(time_series_1,u1,time_series_2,u2,p1,p2)
# plot_velocity_comparison(results_dict)
# plot_phase(results_dict)

# # fs_hz = compute_signal_frequency(time_series)
# # lags12, corr12 = compute_cross_correlation(u1, u2, fs_hz)

# # peak_idx = np.argmax(np.abs(corr12))
# # print(f"Peak correlation = {corr12[peak_idx]:.3f}")
# # print(f"Lag = {lags12[peak_idx]:.4f} s")

# # def collect_component_matrix(df, location_map, component):
# #     """
# #     Build a matrix [time x locations] for one component (ux or uy or uz).
# #     """
# #     cols = []
# #     locs = []
# #     for loc in sorted(location_map.keys()):
# #         cols.append(location_map[loc][component])
# #         locs.append(loc)

# #     data = df[cols].to_numpy(dtype=float)
# #     return locs, data


# # def compute_spatial_correlation_matrix(data):
# #     """
# #     Correlation matrix for one component across locations.
# #     """
# #     return np.corrcoef(data, rowvar=False)


# # def plot_spatial_correlation_matrix(corr_matrix, locs, component):
# #     plt.figure(figsize=(6, 5))
# #     plt.imshow(corr_matrix, vmin=-1, vmax=1)
# #     plt.colorbar(label="Correlation coefficient")
# #     plt.xticks(range(len(locs)), locs)
# #     plt.yticks(range(len(locs)), locs)
# #     plt.title(f"Spatial correlation matrix: {component}")

# #     for i in range(len(locs)):
# #         for j in range(len(locs)):
# #             plt.text(j, i, f"{corr_matrix[i, j]:.2f}", ha="center", va="center")

# #     plt.tight_layout()
# #     plt.savefig(OUTPUT_DIR / f"spatial_corr_matrix_{component}.png", dpi=300)
# #     plt.close()


# # def plot_spatial_correlation_vs_distance(corr_matrix, locs, component):
# #     distances = []
# #     correlations = []

# #     for i in range(len(locs)):
# #         for j in range(i + 1, len(locs)):
# #             if locs[i] in POSITIONS_M and locs[j] in POSITIONS_M:
# #                 d = abs(POSITIONS_M[locs[j]] - POSITIONS_M[locs[i]])
# #                 distances.append(d)
# #                 correlations.append(corr_matrix[i, j])

# #     if len(distances) == 0:
# #         return

# #     distances = np.array(distances)
# #     correlations = np.array(correlations)
# #     order = np.argsort(distances)

# #     plt.figure(figsize=(7, 4.5))
# #     plt.scatter(distances, correlations, s=70)
# #     plt.plot(distances[order], correlations[order], lw=1.2)
# #     plt.xlabel("Separation distance (m)")
# #     plt.ylabel("Correlation")
# #     plt.title(f"Spatial correlation vs distance: {component}")
# #     plt.ylim(-1.05, 1.05)
# #     plt.grid(True, alpha=0.3)
# #     plt.tight_layout()
# #     plt.savefig(OUTPUT_DIR / f"spatial_corr_distance_{component}.png", dpi=300)
# #     plt.close()


# # # ============================================================
# # # 11. CROSS-CORRELATION / COHERENCE
# # # ============================================================



# # def plot_cross_correlation(lags, corr, label, file_tag):
# #     idx = np.argmax(corr)
# #     peak_lag = lags[idx]
# #     peak_val = corr[idx]

# #     plt.figure(figsize=(8, 5))
# #     plt.plot(lags, corr, lw=1.4)
# #     plt.axvline(0, ls="--", lw=1.0)
# #     plt.axvline(peak_lag, ls=":", lw=1.5)
# #     plt.axhline(0, ls="--", lw=1.0)
# #     plt.xlabel("Lag tau (s)")
# #     plt.ylabel("Cross-correlation")
# #     plt.title(f"Cross-correlation: {label}")
# #     plt.grid(True, alpha=0.3)
# #     plt.text(
# #         0.98, 0.95,
# #         f"Peak corr = {peak_val:.3f}\nPeak lag = {peak_lag:.3f} s",
# #         transform=plt.gca().transAxes,
# #         ha="right", va="top",
# #         bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
# #     )
# #     plt.tight_layout()
# #     plt.savefig(OUTPUT_DIR / f"{file_tag}_crosscorr.png", dpi=300)
# #     plt.close()
