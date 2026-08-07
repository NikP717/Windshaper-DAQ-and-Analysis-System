from models.wind.WindsuiteManager import WindsuiteManager
from models.experiment.ExperimentClock import ExperimentClock
from models.wind.WindProfileBuilder import ControlMode, ControlStatus
from models.controllers.ClosedLoopControlManager import ClosedLoopControlManager
from models.wind.FanSelection import FanSelection

import threading

class WindController():
    def __init__(self, config, clock: ExperimentClock) -> None:
        self.clock = clock
        self.config = config
        self.profile = None

        self.open_loop = True
        self.closed_loop_control_manager = None

        self._check_profile_characteristics()

        self.windwrapper = WindsuiteManager(self.config.wall)
        self.stop_event = threading.Event()
        self.check_hz = 20 # Hz, hard coded.

        self.executed_steps = set()

    def run_profile(self) -> None:
        # profile is a list of profile steps, profile step is a list of fan commands
        self.clock.start_timer()
        try:
            while not self.stop_event.is_set():
                if self.stop_event.wait(1 / self.check_hz):
                    break
                time_elapsed = self.clock.timer_time_elapsed
                if time_elapsed >= self.profile.duration:
                    self.stop_event.set()

                self._check_profile_steps(time_elapsed)

                if not self.open_loop:
                    control_instr = self.closed_loop_control_manager.update()
                    all_fans = FanSelection()
                    self.windwrapper.add_instr(all_fans, control_instr)
                    self.windwrapper.apply_instructions()

        except KeyboardInterrupt:
            self.stop_event.set()
        finally:
            if not self.windwrapper.stop_status:
                self.stop_control()

    def stop_control(self) -> None:
        self.windwrapper.stop_windshaper()

    def end_control(self) -> None:
        self.windwrapper.turnoff_windshaper()

    def _check_profile_characteristics(self) -> None:
        self.profile = self.config.profile
        if self.profile.control_status == ControlStatus.CLOSED_LOOP:
            self.open_loop = False
            self.closed_loop_control_manager = ClosedLoopControlManager(self.clock, self.config)

    def _check_profile_steps(self, time_elapsed):
        for i, step in enumerate(self.profile.steps): # multi time step functions
            if self.stop_event.is_set():
                break

            if i not in self.executed_steps and time_elapsed >= step.time:
                for command in step.commands:
                    if self.open_loop:
                        self.windwrapper.add_instr(command.selection,command.instruction)
                        self.windwrapper.apply_instructions()
                        if command.instruction.control_mode == ControlMode.PWM: # pwm executed steps dont need to be repeated so we ignore them once executed
                            # windfunctions need to be evaluated at every time step, so continuously fed through.
                            if command.instruction.pwm_wind_function is not None:
                                self.executed_steps.add(i) 

                    else:
                        if command.instruction.control_mode == ControlMode.VELOCITY: # ensures closed loop profile only follows velocity inputs
                            self.closed_loop_control_manager.change_instr(command.instruction)
                            self.executed_steps.add(i) # adds new velocity condition as logged - closed loop control loops through only most recent logged condition
