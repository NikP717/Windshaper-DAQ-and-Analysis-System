from models.wind.WindsuiteManager import WindsuiteManager
from models.experiment.ExperimentClock import ExperimentClock
from models.wind.WindProfileBuilder import ControlMode
from models.controllers.ClosedLoopControlManager import ClosedLoopControlManager
from models.wind.FanSelection import FanSelection

import threading

class WindController():
    def __init__(self, config, clock: ExperimentClock):
        self.clock = clock
        self.config = config
        self.profile = None

        self.open_loop = True
        self.closed_loop_control_manager = None
        self._check_profile_characteristics()
        self.windwrapper = WindsuiteManager(self.config.wall)

        self.stop_event = threading.Event()
        self.check_hz = 20 # Hz, hard coded.
        
    def _check_profile_characteristics(self):
        self.profile = self.config.profile
        if self.profile.control == ControlMode.CLOSED_LOOP:
            self.open_loop = False
            self.closed_loop_control_manager = ClosedLoopControlManager(self.clock, self.config)

    def run_profile(self):
        # profile is a list of profile steps, profile step is a list of fan commands
        self.clock.start_timer()
        executed_steps = set()
        try:
            while not self.stop_event.is_set():
                time_elapsed = self.clock.timer_time_elapsed

                if time_elapsed >= self.profile.duration:
                    self.stop_event.set()
                    
                for i, step in enumerate(self.profile.steps): # multi time step functions
                    if i not in executed_steps and time_elapsed >= step.time:
                        for command in step.commands:
                            if self.open_loop:
                                self.windwrapper.add_instr(command.selection,command.instruction,command.mode_type.value)
                                self.windwrapper.apply_instructions()
                                if command.mode_type == ControlMode.PWM: # pwm executed steps dont need to be repeated so we ignore them once executed
                                    # windfunctions need to be evaluated at every time step, so continuously fed through.
                                    executed_steps.add(i) 

                            else:
                                if command.mode_type == ControlMode.VELOCITY: # ensures closed loop profile only follows velocity inputs
                                    self.closed_loop_control_manager.change_instr(command.instruction)
                                    executed_steps.add(i) # adds new velocity condition as logged - closed loop control loops through only most recent logged condition

                if not self.open_loop:
                    control_pwm_instr = self.closed_loop_control_manager.update()
                    all_fans = FanSelection()
                    self.windwrapper.add_instr(all_fans, control_pwm_instr,ControlMode.PWM)
                    self.windwrapper.apply_instructions()

        except KeyboardInterrupt:
            self.stop_event.set()
        finally:
            if not self.windwrapper.stop_status:
                self.stop_control()

    def stop_control(self):
        self.windwrapper.stop_windshaper()

    def end_control(self):
        self.windwrapper.turnoff_windshaper()