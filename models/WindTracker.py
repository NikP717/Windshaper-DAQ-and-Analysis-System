import threading
import time
from windsuite_sdk import TrackingData
from scipy.spatial.transform import Rotation as R
import numpy as np
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
import logging

logger = logging.getLogger(__name__)


class WindTracker():
    """Class which controls Windsuite SDK Camera tracking callback technology and output coordinates whilst
    enabling user live zeroing for experimental positioning.
    
    NOTE: In this current version this is not really applicable nor functional - coordinates are not accurate and involve cross-coupled movement of axis.
    For anyone with a more developed tracking camera system maybe it does work - I havent confirmed if its a camera issue or code issue."""

    def __init__(self,active_windshaper_instance, active_probe_instance) -> None:
        """Initialises all coordinate positions including quaternions, and stores active windshaper and probe instances for callback."""
        self.zero_position = None
        self.zero_rot = None
        self.zero_rot_inv = None

        self.zero_samples = []
        self.zero_time = 3

        self.start_zero_time = time.time()

        self.stop_event = threading.Event()
        self.windshaper = active_windshaper_instance
        self.freq = 25 #Hz
        #Positional and Angular Storage
        self.posx = 0
        self.posy = 0
        self.posz = 0
        self.rotw = 0
        self.rotx = 0
        self.roty = 0
        self.rotz = 0

        #Tracking bool
        self.is_tracking = False
        self.tracking_fail_notification = False

        # TODO: MAKE THIS WORK FOR NEWPROBE - HAVENT BEEN ABLE TO TEST
        if active_probe_instance.tracking_ID == 1: # Old probe hard coded ID
            self.track_obj_name = "windprobold_e"
        else:
            self.track_obj_name = "" # TEMP UNTIL NEW PROBE

    def telemetry_table(self) -> None:
        """Function which creates a live telemetry table for the user to see."""
        table = Table(title="Wind Probe Tracking Telemetry", expand=True)
        table.add_column("Parameter", justify="left")
        table.add_column("Value", justify="right")
        # Position conversion
        x_cm = self.posx * 100
        y_cm = self.posy * 100
        z_cm = self.posz * 100
        # Quaternion -> Euler degrees
        quat = [
            self.rotx,
            self.roty,
            self.rotz,
            self.rotw
        ]
        try:
            euler = R.from_quat(quat).as_euler("xyz", degrees=True)

            roll = euler[0]
            pitch = euler[1]
            yaw = euler[2]

        except Exception:
            roll = pitch = yaw = 0
        
        if self.zero_position is not None:
            if self.is_tracking:
                status_msg = "✓ CONNECTED"
            else:
                status_msg = "✗ LOST: Check WindVision Connection, positioning and wiring."
        else:
            status_msg = "⚠︎ ZEROING POSITION: DO NOT MOVE ANY EQUIPMENT."
        table.add_row("Tracking", status_msg)

        table.add_row("", "")
        
        table.add_row("X Position", f"{x_cm:8.1f} cm")
        table.add_row("Y Position", f"{y_cm:8.1f} cm")
        table.add_row("Z Position", f"{z_cm:8.1f} cm")

        table.add_row("", "")

        table.add_row("Roll", f"{roll:8.1f}°")
        table.add_row("Pitch", f"{pitch:8.1f}°")
        table.add_row("Yaw", f"{yaw:8.1f}°")
        return Panel(table)

    def display_tracking(self):
        """Function which displays live telemetry table at 10 FPS."""
        with Live(self.telemetry_table(),refresh_per_second=10) as live:
            while not self.stop_event.is_set():
                live.update(self.telemetry_table())
                time.sleep(0.1)

    def start(self) -> None:
        """Function which starts windshaper tracking callback and display of tracking."""
        self.windshaper.windshaper.register_tracking_callback(callback=self._on_tracking_data)
        try:
            logger.info("Starting Tracking, press CTRL+C to end, press SPACE to zero coordinate system.")
            self.display_tracking()
                
        except KeyboardInterrupt:
            self.stop_event.set()
            logger.info("Ended tracking.")

    def _on_tracking_data(self, data: dict[str, TrackingData]):
        """Function which acts as WindSuite SDK callback for tracking data.
        NOTE: Quaternion and relative coordinate calculations were coded with support of AI."""
        for object_name, tracking_data in data.items():

            # Match object name
            if str(object_name).lower().strip() != self.track_obj_name.lower().strip():
                continue

            # If not tracked, update flag and skip
            if not tracking_data.is_tracked:
                self.is_tracking = False
                continue
            else:
                self.is_tracking = True

            # -----------------------------
            # INITIALISE ZERO COORDS
            # -----------------------------
            if self.zero_position is None and self.zero_rot is None:
                t_elapsed = time.time() - self.start_zero_time
                if t_elapsed <= self.zero_time:
                    self.zero_samples.append(tracking_data)
                    return # pass position calculations for now
                else:
                    xs = [s.position_meters_world_ref.x for s in self.zero_samples]
                    ys = [s.position_meters_world_ref.y for s in self.zero_samples]
                    zs = [s.position_meters_world_ref.z for s in self.zero_samples]
                    avg_position = np.array([np.mean(xs),np.mean(ys),np.mean(zs)])
                    self.zero_position = avg_position
                    # mean sample rotation
                    rotations = []
                    for s in self.zero_samples:
                        q = [
                            s.rotation_world_ref.x,
                            s.rotation_world_ref.y,
                            s.rotation_world_ref.z,
                            s.rotation_world_ref.w
                        ]
                        rotations.append(R.from_quat(q))
                    # average rotations
                    avg_rot = R.concatenate(rotations).mean()
                    self.zero_rot = avg_rot
                    self.zero_rot_inv = self.zero_rot.inv()
            # -----------------------------
            # POSITION (RELATIVE + AXIS ALIGNED)
            # -----------------------------
            if self.zero_position is None or self.zero_rot_inv is None: # additional handguard incase callback comes through before assignment
                return
            pos = tracking_data.position_meters_world_ref

            # Subtract zero position
            raw_pos_vec = np.array([pos.x,pos.y,pos.z]) - self.zero_position

            # Rotate into zeroed frame
            aligned_pos = self.zero_rot_inv.apply(raw_pos_vec)

            self.posx, self.posy, self.posz = aligned_pos

            # -----------------------------
            # ROTATION (RELATIVE QUATERNION)
            # -----------------------------
            rot = tracking_data.rotation_world_ref

            q = [rot.x, rot.y, rot.z, rot.w]

            relative_rotation = self.zero_rot_inv * R.from_quat(q)
            relative_quat = relative_rotation.as_quat()

            self.rotx = relative_quat[0]
            self.roty = relative_quat[1]
            self.rotz = relative_quat[2]
            self.rotw = relative_quat[3]
        
    def reset_position(self):
        self.zero_position = None
        self.zero_rot = None
        self.zero_rot_inv = None
        self.zero_samples = []
        self.start_zero_time = time.time()
