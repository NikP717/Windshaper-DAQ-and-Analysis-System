import threading
import logging

from models.wind.WindsuiteManager import WindsuiteManager
from models.experiment.ExperimentClock import ExperimentClock
from models.wind.WindProfileBuilder import ControlMode, ControlStatus
from models.controllers.ClosedLoopControlManager import ClosedLoopControlManager

logger = logging.getLogger(__name__)

class WindController():
    """Class which operates open and closed loop profile control by communicating with WindSuiteManager"""
    def __init__(self, config, clock: ExperimentClock) -> None:
        """Initialises windsuitemanager -> connection to windsuite,  profile mode and executed steps."""
        logger.info("Initialised.")
        self.clock = clock
        self.config = config
        self.profile = None

        self.open_loop = True
        self.closed_loop_control_manager = None

        # checks if open or closed loop operation required.
        self._check_profile_characteristics()

        self.windwrapper = WindsuiteManager(self.config.wall)
        self.stop_event = threading.Event()
        self.check_hz = 20 # Hz, hard coded.

        self.executed_steps = set()

    def run_profile(self) -> None:
        """Function for DeviceManager thread for operating the windshaper user inputted profiles.
        This function works for both open and closed loop configurations (hence the nested if situation going on). """
        self.clock.start_timer()
        try:
            while not self.stop_event.is_set():
                # loop frequency limitation on hard coded frequency
                if self.stop_event.wait(1 / self.check_hz):
                    break

                # time check
                time_elapsed = self.clock.timer_time_elapsed
                if time_elapsed >= self.profile.duration:
                    self.stop_event.set()

                self._check_profile_steps(time_elapsed) # handles open loop operations too

                # closed loop management
                if not self.open_loop:
                    # if statement handles control initialisation logic within control loop manager.
                    if not self.closed_loop_control_manager.control_init:
                        # if not wind function initialised
                        control_instr = self.closed_loop_control_manager.update()
                        if control_instr:
                            # goes through control instructions which establish the live modifiable wind functions closed loop manages
                            for select, instr in control_instr:
                                self.windwrapper.add_instr(select, instr)
                            self.windwrapper.apply_instructions()
                    else:
                        # if initialised just updates the parameters within the existing wind functions control loop manages
                        self.closed_loop_control_manager.update()
                        self.windwrapper.apply_instructions()

        except KeyboardInterrupt:
            self.stop_event.set()
        finally:
            if not self.windwrapper.stop_status:
                self.stop_control()

    def stop_control(self) -> None:
        """Function which immediately stops the windshaper and closed loop control manager."""
        self.windwrapper.stop_windshaper()
        if self.closed_loop_control_manager is not None:
            self.closed_loop_control_manager.stop()

    def end_control(self) -> None:
        """Function which acts as a switch off for the windshaper connection and PSUs."""
        self.windwrapper.turnoff_windshaper()

    def _check_profile_characteristics(self) -> None:
        """Function which checks whether or not a profile is open or closed loop operating, if closed it initialises the CloseLoopControlManager."""
        self.profile = self.config.profile
        if self.profile.control_status == ControlStatus.CLOSED_LOOP:
            self.open_loop = False
            self.closed_loop_control_manager = ClosedLoopControlManager(self.clock, self.config)

    def _check_profile_steps(self, time_elapsed: float) -> None:
        """My Favourite Helper Function:
        Main Purpose: Convert user created WindProfiles into WindSuiteManager commands. 
        The nested for loop is because a WindProfile is a list of ProfileSteps which is a list of FanCommands (see WindProfileBuilder).

        This function checks for PWM commands that are not executed (within self.executed_steps), and exceed their time of activation.

        Logic: WindController stores executed steps -> Only discrete PWM commands and Velocity Commands. NOT wind functions.
        -> The reason: Windfunctions MUST be continously applied to Windsuite SDK at each time step to be evaluated, other commands do not, so theyre not registered as completed.
        Velocity commands are not logged although continous because ClosedLoopControlManager continously feeds its own discrete PWM inputs - see controllers for more."""

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
                            if command.instruction.pwm_wind_function is None:
                                self.executed_steps.add(i) 

                    else:
                        if command.instruction.control_mode == ControlMode.VELOCITY: # ensures closed loop profile only follows velocity inputs, and not erronious PWM ones
                            self.closed_loop_control_manager.change_instr(command.instruction)
                            self.executed_steps.add(i) # adds new velocity condition as logged - closed loop control loops through only most recent logged condition
