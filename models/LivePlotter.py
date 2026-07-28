import multiprocessing as mp
from collections import deque
import numpy as np

import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore


class LivePlotter:
    def __init__(self, probe_instance_ID, probe_plot=False, wind_plot=False, fan_shape = None | tuple,  max_points=100000):

        self.max_points = max_points
        self.q = mp.Queue(maxsize=10000)
        self.probe_plot = probe_plot
        self.wind_plot = wind_plot
        self.fan_shape = fan_shape
        self.probe_id = probe_instance_ID

        self.proc = mp.Process(
            target=self._gui_process,
            args=(self.q, self.max_points),
            daemon=True,
        )

        self.proc.start()

    def push(self, row):
        """Non-blocking."""
        try:
            self.q.put_nowait(row)
        except:
            pass

    def close(self):
        if self.proc.is_alive():
            self.proc.terminate()
            self.proc.join(timeout=2)

    def _gui_process(self, q, max_points):

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

            curve_pwm = fan_plot.plot(pen='g', name="PWM")
            curve_ps = fan_plot.plot(pen="r", name= "PWM STD")

            rpm_plot = shaper.addPlot(row=1, col=0, title="Fan RPM")
            r_legend = rpm_plot.addLegend()
            rpm_plot.showGrid(x=True, y=True, alpha=0.25)

            curve_rpm = rpm_plot.plot(pen='g', name="RPM")
            curve_rs = rpm_plot.plot(pen='b', name="RPM STD")


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
            pwm = deque(maxlen=max_points)
            rpm = deque(maxlen=max_points)
            rs = deque(maxlen=max_points)
            ps = deque(maxlen=max_points)

            downstream_rpm = np.zeros(self.fan_shape)
            upstream_rpm = np.zeros(self.fan_shape)
            

        def fan_array_to_matrix(rpm_array):

            modules = np.array(rpm_array[0]).reshape(-1, 3, 3)

            rows = int(np.sqrt(len(modules)))

            module_rows = []

            for i in range(rows):
                module_rows.append(
                    np.hstack(modules[i*rows:(i+1)*rows])
                )

            downstream = np.vstack(module_rows)
            downstream = np.rot90(downstream,k=-1)

            modules = np.array(rpm_array[1]).reshape(-1, 3, 3)

            module_rows = []

            for i in range(rows):
                module_rows.append(
                    np.hstack(modules[i*rows:(i+1)*rows])
                )

            upstream = np.vstack(module_rows)
            upstream =  np.rot90(upstream,k=-1) # this is a temporary fix because i havent understood modules callback indexing yet, im sorry future me
            return downstream, upstream


        timer = QtCore.QTimer()

        def update():
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
                    pwm.append(row[7])
                    rpm.append(row[8])
                    rs.append(row[11])
                    ps.append(row[10])
                    try:
                        downstream_rpm, upstream_rpm = fan_array_to_matrix(row[13])
                    except ValueError:
                        pass

            if self.probe_plot:
                curve_x.setData(t_pr, x)
                curve_y.setData(t_pr, y)
                curve_z.setData(t_pr, z)
                curve_p.setData(t_pr, p)

            if self.wind_plot:
                curve_pwm.setData(t_ws, pwm)
                curve_ps.setData(t_ws, ps)
                curve_rpm.setData(t_ws, rpm)
                curve_rs.setData(t_ws, rs)
                downstream_img.setImage(downstream_rpm, autoLevels=False)
                upstream_img.setImage(upstream_rpm, autoLevels=False)

            def update_legend(legend, values):
                for sample, (_, label) in zip(values, legend.items):
                    label.setText(sample)

            if self.probe_plot and len(x):
                update_legend(v_legend,[f"Vx: {x[-1]:.3f} m/s",f"Vy: {y[-1]:.3f} m/s",f"Vz: {z[-1]:.3f} m/s"])
                update_legend(p_legend,[f"Stat P: {p[-1]:.0f} Pa"])

            if self.wind_plot and len(rpm):
                update_legend(r_legend,[f"Mean RPM: {rpm[-1]:.0f}",f"RPM STD: {rs[-1]:.0f}"])
                update_legend(f_legend,[f"Mean PWM: {pwm[-1]:.0f}",f"PWM STD: {ps[-1]:.0f}"])

        timer.timeout.connect(update)
        timer.start(33)

        app.exec()