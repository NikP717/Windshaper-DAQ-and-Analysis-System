from models.data.ControlFeedbackState import ControlFeedbackState
from models.experiment.ExperimentClock import ExperimentClock
from models.experiment.ExperimentConfig import ExperimentConfig
from models.wind.WindProfileBuilder import FanInstruction
from models.controllers.VelocityControl import VelocityControl
from models.controllers.TurbulenceControl import TurbulenceControl
from models.controllers.TurbulenceSpectralControl import TurbulenceSpectralControl
from models.controllers.ControlWindFunction import ControlWindFunction
from models.controllers.ControlWindFunction import LiveSineWindFunction

import threading
import numpy as np


class ClosedLoopControlManager():
    def __init__(self, clock: ExperimentClock, config: ExperimentConfig) -> None:
        self.clock = clock
        self.config = config
        self.stop_status = threading.Event()
        turbulence_status = self.config.profile.turbulence_control 

        #Controllers
        self.velocity_controller = VelocityControl()
        self.turbulence_controller = None
        self.spectral_controller = None

        if turbulence_status:
            self.turbulence_controller = TurbulenceControl(self.config)
            self.spectral_controller = TurbulenceSpectralControl()


        # Profile Manager
        self.output_windfunction = ControlWindFunction()

        # Controller init flag
        self.control_init = False

        self.TURBULENCE_START_TIME = 20

        self._generate_sines_for_feedback()

    def stop(self):
        self.stop_status.set()

    def change_instr(self, new_command: FanInstruction) -> None:
        ControlFeedbackState.target_velocity = new_command.velocity
        ControlFeedbackState.velocity_component = new_command.velocity_component

        if new_command.TI is not None:
            ControlFeedbackState.target_TI = new_command.TI /100

        if new_command.target_spectral_content is not None:
            ControlFeedbackState.set_target_spectrum(new_command.target_spectral_content)

        if new_command.TI and self.turbulence_controller is None:
            self.turbulence_controller = TurbulenceControl(self.config)
            self.spectral_controller = TurbulenceSpectralControl()

        self.velocity_controller.refresh_controller()
        if self.turbulence_controller:
            self.turbulence_controller.refresh_controller()
        if self.spectral_controller:
            self.spectral_controller.refresh_controller()

    def update(self) -> int:
        if self.stop_status.is_set():
            return

        ControlFeedbackState.change_time(self.clock) # updates dt used by PID
        self.velocity_controller.update()
        # turbulence control occurs once system stabilises on a velocity
        if self.clock.time_elapsed > self.TURBULENCE_START_TIME:
            if self.turbulence_controller:
                self.turbulence_controller.update()
                self.spectral_controller.update()

        if not self.control_init:
            fan_command = self.output_windfunction.init()
            self.control_init = True
            return fan_command

    def _generate_sines_for_feedback(self):
        frequencies = np.arange(0.05, 0.65, 0.05)
        rng = np.random.default_rng(42) # repeatable phase randomiser for individual frequency sines
        ControlFeedbackState.set_sines([LiveSineWindFunction(frequency=frequency, rng = rng) for frequency in frequencies])