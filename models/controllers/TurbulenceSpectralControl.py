from models.data.ControlFeedbackState import ControlFeedbackState
from models.wind.WindProfileBuilder import SpectralContent
from models.wind.WindProfileBuilder import Vel
from models.data.ProbeFeedbackState import ProbeFeedbackState

import math
import numpy as np

class TurbulenceSpectralControl():
    """Class which controls sine amplitudes based on total turbulence PWM setting within ControlFeedbackState: Takes user inputs to generate
    custom spectral peaks, if no peaks will generate a uniform discrete spectrum distribution"""
    def __init__(self) -> None:
        self.KP = 0.8
        self.KI = 0
        self.KD = 0
        self.SPECTRAL_TAU = 50
        self.MEAN_TAU = 2

        self.ADDIT_FQ_GAIN_DICT = {
            0.05: 1,
            0.10: 1,
            0.15: 1,
            0.20: 1,
            0.25: 1,
            0.30: 1,  
            0.35: 1,
            0.40: 1,
            0.45: 1,
            0.50: 1,
            0.55: 2,
            0.60: 2
        }

        self.statistics = SpectralAmplitudeStats(self._get_frequency_list(), self.SPECTRAL_TAU, self.MEAN_TAU, dt=0.01)

    def update(self) -> None:
        current_velocity = self._get_probe_windspeed()
        self.statistics.update(current_velocity, ControlFeedbackState.dt)
        self._generate_absolute_amplitude_targets()

        new_abs_amplitudes = {}
        for sines in ControlFeedbackState.frequency_band_sines:
            if sines is not None:
                target = sines.target_absolute_amplitude
                measurement = self.statistics.amplitude(sines.frequency)
                controller = sines.controller
                raw_amplitude_correction = controller.update(target, measurement, ControlFeedbackState.dt)
                new_abs_amplitudes[sines.frequency] = (raw_amplitude_correction + sines.amplitude)

        for sines in ControlFeedbackState.frequency_band_sines:
            if sines is not None:
                cmd = new_abs_amplitudes[sines.frequency]  * self.ADDIT_FQ_GAIN_DICT[sines.frequency]
                sines.update_amplitude(max(0.0, cmd))
                # print(f"FQ: {sines.frequency:.2f}, REL AMP: {self.statistics.relative_amplitude(sines.frequency):.2f}, TARGET REL AMP: {sines.target_relative_amplitude:.2f}")

        print(
        f"[FQ {sines.frequency:.2f}] "
        f"target_abs={sines.target_absolute_amplitude:.4f} | "
        f"measured={measurement:.4f} | "
        f"rawPID={raw_amplitude_correction:.4f} | "
        f"cmd={cmd:.4f} | "
        f"rel={self.statistics.relative_amplitude(sines.frequency):.4f} | "
        f"target_rel={sines.target_relative_amplitude:.4f}")

    def refresh_controller(self) -> None:
        self._assign_sine_controllers()
        if hasattr(ControlFeedbackState, 'target_spectral_content'):
            ControlFeedbackState.set_target_spectrum()
        else:
            ControlFeedbackState.set_target_spectrum(self._generate_uniform_spectral_instr())

    def _generate_absolute_amplitude_targets(self) -> None:
        total_pwm = ControlFeedbackState.baseline_turbulence_pwm + ControlFeedbackState.correction_turbulence_pwm

        rel = [sines.target_relative_amplitude for sines in ControlFeedbackState.frequency_band_sines if sines is not None]
        norm = math.sqrt(sum(r*r for r in rel))

        for sines in ControlFeedbackState.frequency_band_sines:
            if sines is not None:
                sines.target_absolute_amplitude = (sines.target_relative_amplitude / norm) * total_pwm

    def _assign_sine_controllers(self) -> None:
        for sines in ControlFeedbackState.frequency_band_sines:
            if sines is not None:
                sines.set_controller(self.KP, self.KI, self.KD)

    def _generate_uniform_spectral_instr(self) -> None:
        frequency_list = self._get_frequency_list()
        new_spectrum = SpectralContent(frequency_amplitude_dict={})
        for fq in frequency_list:
            new_spectrum.frequency_amplitude_dict[fq] = 1
        return new_spectrum

    def _get_frequency_list(self) -> None:
        frequency_list = []
        for sines in ControlFeedbackState.frequency_band_sines:
            if sines is not None:
                frequency_list.append(sines.frequency)
        return frequency_list

    def _get_probe_windspeed(self) -> float:
        v_component = ControlFeedbackState.velocity_component
        if v_component == Vel.X:
            return ProbeFeedbackState.windspeed_x
        if v_component == Vel.Y:
            return ProbeFeedbackState.windspeed_y
        if v_component == Vel.Z:
            return ProbeFeedbackState.windspeed_z
        
class SpectralAmplitudeStats:
    """Class which is utilised by TurbulenceSpectralControl to determine currently cos and sin fitted spectral absolute and relative amplitude.
    NOTE: TBC on accuracy, mathematics supported by AI."""
    def __init__(self, frequencies: list, spectral_tau: float, mean_tau: float, dt: float) -> None:
        """Initialises gains, sin and cos frequency array and alpha coefficients."""
        self.frequencies = frequencies
        self.spectral_tau = spectral_tau
        self.mean_tau = mean_tau
        self.spectral_alpha = math.exp(-dt / spectral_tau)
        self.mean_alpha = math.exp(-dt / mean_tau)
        self.cos = {frequency: 0.0 for frequency in frequencies}
        self.sin = {frequency: 0.0 for frequency in frequencies}
        self.mean = None
        self.time = 0.0
        self.initialised = False

    def update(self, x: float, dt: float) -> None:
        self.spectral_alpha = math.exp(-dt / self.spectral_tau)
        self.mean_alpha = math.exp(-dt / self.mean_tau)

        if math.isnan(x):
            self.time += dt
            return

        if self.mean is None:
            self.mean = x
            self.time += dt
            return

        self.mean = self.mean_alpha * self.mean + (1 - self.mean_alpha) * x

        for frequency in self.frequencies:
            phase = 2 * math.pi * frequency * self.time
            self.cos[frequency] = self.spectral_alpha * self.cos[frequency] + (1 - self.spectral_alpha) * x * math.cos(phase)
            self.sin[frequency] = self.spectral_alpha * self.sin[frequency] + (1 - self.spectral_alpha) * x* math.sin(phase)

        self.time += dt
        self.initialised = True

    def amplitude(self, frequency: float) -> float:
        if not self.initialised:
            return 0.0

        return 2 * math.sqrt(self.cos[frequency] ** 2 + self.sin[frequency] ** 2)

    def relative_amplitude(self, frequency: float) -> float:
        amplitudes = {f: self.amplitude(f) for f in self.frequencies}
        total = math.sqrt(sum(amplitude ** 2 for amplitude in amplitudes.values()))

        if total == 0:
            return 0.0

        return amplitudes[frequency] / total

    def reset(self) -> None:
        self.cos = {frequency: 0.0 for frequency in self.frequencies}
        self.sin = {frequency: 0.0 for frequency in self.frequencies}
        self.mean = None
        self.time = 0.0
        self.initialised = False
