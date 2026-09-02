import multiprocessing as mp
from collections import deque
import numpy as np
import time
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore


class LivePlotter:
    """Class which plots live inputted telemetry for wind and probe data spefifically. Operates on a multiprocess which resides within each Probe instance.
    NOTE: Due to my lack of understanding of Qt Widgets - This code was heavily guided with AI support."""

    def __init__(self, probe_instance_ID: str, probe_plot=False, wind_plot=False, fan_shape = None | tuple,  max_points=100000) -> None:
        """Initialises multiprocess of GUI generation and starts the multiprocess."""

        self.max_points = max_points
        self.q = mp.Queue(maxsize=10000)
        self.probe_plot = probe_plot
        self.wind_plot = wind_plot
        self.fan_shape = fan_shape
        self.probe_id = probe_instance_ID
        self.shutdown = mp.Event()

        self.proc = mp.Process(
            target=self._gui_process,
            args=(self.q, self.max_points, self.shutdown),
            daemon=True,
        )

        self.proc.start()

    def push(self, row: list) -> None:
        """Function which pushes data rows from probe instances to data queues."""
        try:
            self.q.put_nowait(row)
        except:
            pass

    def close(self) -> None:
        """Function which closes multiprocess and gui of live plotting."""
        if self.proc.is_alive():
            self.shutdown.set() 
            self.proc.join(timeout=2)

    def _gui_process(self, q, max_points, shutdown_status) -> None:
        """Helper function which manages updates of plot and also plot graphics."""
        app = QtWidgets.QApplication([])

        # ================= WindProbe =================
        if self.probe_plot:
            probe = pg.GraphicsLayoutWidget(show=True, title=f"WindProbe ID = {self.probe_id} Live Data")
            probe.resize(600, 400)

            velocity_plot = probe.addPlot(row=0, col=0, title="Probe Velocity")
            v_legend = velocity_plot.addLegend()
            velocity_plot.showGrid(x=True, y=True, alpha=0.25)

            curve_x = velocity_plot.plot(pen='r', name="Vx")
            curve_y = velocity_plot.plot(pen='g', name="Vy")
            curve_z = velocity_plot.plot(pen='b', name="Vz")

            pressure_plot = probe.addPlot(row=1, col=0, title="Probe Pressure")
            p_legend = pressure_plot.addLegend()
            pressure_plot.showGrid(x=True, y=True, alpha=0.25)

            curve_p = pressure_plot.plot(pen='c', name="Pressure")


        # ================= WindShaper =================

        
        if self.wind_plot:
            shaper = pg.GraphicsLayoutWidget(show=True, title="WindShaper Live Data")
            shaper.resize(600, 400)

            fan_plot = shaper.addPlot(row=0, col=0, title="Fan PWM")
            f_legend = fan_plot.addLegend()
            fan_plot.showGrid(x=True, y=True, alpha=0.25)
            
            curve_up_pwm = fan_plot.plot(pen='g', name="PWM Upstream")
            curve_down_pwm = fan_plot.plot(pen='b', name="PWM Downstream")

            rpm_plot = shaper.addPlot(row=1, col=0, title="Fan RPM")
            r_legend = rpm_plot.addLegend()
            rpm_plot.showGrid(x=True, y=True, alpha=0.25)

            curve_up_rpm = rpm_plot.plot(pen='g', name="RPM Upstream")
            curve__up_rs = rpm_plot.plot(pen='r', name="RPM STD Upstream")

            curve_down_rpm = rpm_plot.plot(pen='b', name="RPM Downstream")
            curve_down_rs = rpm_plot.plot(pen="magenta", name="RPM STD Downstream")


            # ================= Fan Map =================

            fan_map = pg.GraphicsLayoutWidget(show=True, title="WindShaper RPM Map")
            fan_map.resize(300, 400)

            downstream_plot = fan_map.addPlot(row=0, col=0, title="Downstream RPM")
            upstream_plot = fan_map.addPlot(row=1, col=0, title="Upstream RPM")

            downstream_img = pg.ImageItem()
            upstream_img = pg.ImageItem()

            cmap = pg.colormap.get("viridis")

            downstream_plot.addItem(downstream_img)
            upstream_plot.addItem(upstream_img)

            downstream_bar = pg.ColorBarItem(values=(0,14000), colorMap=cmap, label="RPM")
            upstream_bar = pg.ColorBarItem(values=(0,14000), colorMap=cmap, label="RPM")

            downstream_bar.setImageItem(downstream_img)
            upstream_bar.setImageItem(upstream_img)

            fan_map.addItem(downstream_bar, row=0, col=1)
            fan_map.addItem(upstream_bar, row=1, col=1)

            downstream_img.setColorMap(cmap)
            upstream_img.setColorMap(cmap)

            downstream_img.setLevels([0,14000])
            upstream_img.setLevels([0,14000])

            downstream_img.setImage(np.zeros(self.fan_shape), autoLevels=False)
            upstream_img.setImage(np.zeros(self.fan_shape), autoLevels=False)

            downstream_plot.showGrid(x=True, y=True, alpha=0.25)
            upstream_plot.showGrid(x=True, y=True, alpha=0.25)


        # ================= Buffers =================
        if self.probe_plot:
            t_pr = deque(maxlen=max_points)
            x = deque(maxlen=max_points)
            y = deque(maxlen=max_points)
            z = deque(maxlen=max_points)
            p = deque(maxlen=max_points)
        if self.wind_plot:
            t_ws = deque(maxlen=max_points)
            pwm_up = deque(maxlen=max_points)
            pwm_down = deque(maxlen=max_points)
            rpm_up = deque(maxlen=max_points)
            rpm_down = deque(maxlen=max_points)
            rs_up = deque(maxlen=max_points)
            rs_down = deque(maxlen=max_points)

            downstream_rpm = np.zeros(self.fan_shape)
            upstream_rpm = np.zeros(self.fan_shape)

        timer = QtCore.QTimer()

        def update() -> None:
            """Sub function which uses the most recent row and slices it for appropriate data deques of each variable for plotting.
            Function also dynamically updates legend text to display current values of the plot."""
            if self.wind_plot:
                nonlocal downstream_rpm, upstream_rpm

            while True:
                try:
                    row = q.get_nowait()
                except:
                    break

                if self.probe_plot:
                    t_pr.append(row[0])
                    x.append(row[1])
                    y.append(row[2])
                    z.append(row[3])
                    p.append(row[4])

                if self.wind_plot:
                    t_ws.append(row[0])
                    pwm_up.append(row[7])
                    rpm_up.append(row[8])
                    rs_up.append(row[9])

                    pwm_down.append(row[11])
                    rpm_down.append(row[12])
                    rs_down.append(row[13])

                    upstream_rpm = row[10]
                    downstream_rpm = row[14]
            if self.probe_plot:
                curve_x.setData(t_pr, x)
                curve_y.setData(t_pr, y)
                curve_z.setData(t_pr, z)
                curve_p.setData(t_pr, p)

            if self.wind_plot:
                curve_up_pwm.setData(t_ws, pwm_up)
                curve_down_pwm.setData(t_ws, pwm_down)

                curve_up_rpm.setData(t_ws, rpm_up)
                curve_down_rpm.setData(t_ws, rpm_down)

                curve__up_rs.setData(t_ws, rs_up)
                curve_down_rs.setData(t_ws, rs_down)

                # Need to rotate so display shows it intuitively
                upstream_rpm = np.rot90(upstream_rpm, k=-1)
                downstream_rpm = np.rot90(downstream_rpm, k=-1)
                downstream_img.setImage(downstream_rpm, autoLevels=False)
                upstream_img.setImage(upstream_rpm, autoLevels=False)

            def update_legend(legend, values):
                for sample, (_, label) in zip(values, legend.items):
                    label.setText(sample)

            if self.probe_plot and len(x):
                update_legend(v_legend,[f"Vx: {x[-1]:.3f} m/s",f"Vy: {y[-1]:.3f} m/s",f"Vz: {z[-1]:.3f} m/s"])
                update_legend(p_legend,[f"Stat P: {p[-1]:.0f} Pa"])

            if self.wind_plot and len(rpm_up):
                update_legend(r_legend,[f"Mean Upstream RPM: {rpm_up[-1]:.0f}",f"RPM Upstream STD: {rs_up[-1]:.0f}",f"Mean Downstream RPM: {rpm_down[-1]:.0f}",f"RPM Downstream STD: {rs_down[-1]:.0f}"])
                update_legend(f_legend,[f"Mean Upstream PWM: {pwm_up[-1]:.0f}",f"Mean Downstream PWM: {pwm_down[-1]:.0f}"])

        timer.timeout.connect(update)
        timer.start(33)

        # app.exec()
        # manual event loop instead to ensure clean exit
        while not shutdown_status.is_set():
            app.processEvents()
            time.sleep(0.01)

        app.quit()