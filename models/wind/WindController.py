from models.wind.WindsuiteManager import WindsuiteManager
from models.experiment.ExperimentClock import ExperimentClock
from models.wind.WindProfileBuilder import WindProfile

import threading

class WindController():
    def __init__(self, fan_wall_selection, clock: ExperimentClock):
        self.windwrapper = WindsuiteManager(fan_wall_selection)
        self.clock = clock

        self.stop_event = threading.Event()
        self.check_hz = 20 # Hz, hard coded.
        
    def run_profile(self, profile: WindProfile):
        # profile is a list of profile steps, profile step is a list of fan commands
        self.clock.start_timer()
        executed_steps = set()

        while not self.stop_event.wait(1/self.check_hz):

            time_elapsed = self.clock.timer_time_elapsed

            if time_elapsed >= profile.duration:
                self.stop_event.set()

            for i, step in enumerate(profile.steps): # multi time step functions
                if i not in executed_steps and time_elapsed >= step.time:
                    for command in step.commands:
                        self.windwrapper.add_instr(command.selection,command.instruction,command.mode_type)
            
                    self.windwrapper.apply_instructions()

                    executed_steps.add(i) # better than adding the step function

        if not self.windwrapper.stop_status:
            self.stop_control()

    def stop_control(self):
        self.windwrapper.stop_windshaper()

    def end_control(self):
        self.windwrapper.turnoff_windshaper()