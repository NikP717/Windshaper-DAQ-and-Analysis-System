from __future__ import annotations
from models.experiment.ExperimentClock import ExperimentClock
from models.wind.WindProfileBuilder import SpectralContent, Vel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Prevent circular import issue
    from models.controllers.ControlWindFunction import LiveSineWindFunction

from typing import ClassVar
from dataclasses import dataclass

@dataclass
class ControlFeedbackState:
    # CONTROL INPUTS
    target_velocity: ClassVar[float] = 0
    target_TI: ClassVar[float] = 0 # %
    target_spectral_content: ClassVar[SpectralContent]
    velocity_component: ClassVar[Vel]

    # CONTROL OUTPUTS
    mean_velocity_pwm: ClassVar[float] = 0
    baseline_turbulence_pwm: ClassVar[float] = 0
    correction_turbulence_pwm: ClassVar[float] = 0
    # SPECTRAL STORAGE
    # frequency range split into control from 12 discrete sine frequencies distributed across frequency range
    frequency_range: ClassVar[range]
    frequency_band_sines: ClassVar[list[LiveSineWindFunction]]

    # TIME MANAGEMENT
    last_recorded_time: ClassVar[float] = 0
    dt: ClassVar[float] = 0.01 

    @classmethod
    def change_time(cls, clock: ExperimentClock) -> None:
        current_time = clock.time_elapsed
        cls.dt = current_time - cls.last_recorded_time
        cls.last_recorded_time = current_time
        
    @classmethod
    def set_sines(cls, sines: list[LiveSineWindFunction]) -> None:
        cls.frequency_band_sines = sines

    @classmethod
    def set_target_spectrum(cls, target_spectral: SpectralContent = None):
        if target_spectral:
            spectral_dict = target_spectral.frequency_amplitude_dict
        else:
            spectral_dict = cls.target_spectral_content.frequency_amplitude_dict

        for sines in cls.frequency_band_sines: # quickly reset all amplitudes from past spectrum
            sines.target_amplitude = 0.0

        for fq, amplitude in spectral_dict.items():
            for sines in cls.frequency_band_sines:
                if sines.frequency == fq:
                    sines.target_amplitude = amplitude

        cls.target_spectral_content = SpectralContent(spectral_dict)
