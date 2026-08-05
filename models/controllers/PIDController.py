from typing import Optional
from dataclasses import dataclass
import math

@dataclass
class PIDController():
    kp: float = 2
    ki: float = 0.8
    kd: float = 0.2
    
    # Output limits
    output_min: Optional[float] = -20
    output_max: Optional[float] = 20

    # Anti-windup
    anti_windup_gain: float = 1.0

    # Derivative filter time constant (seconds)
    derivative_filter_tau: float = 0.05

    # Derivative on measurement avoids setpoint kick
    derivative_on_measurement: bool = True

    def __post_init__(self):
        self.reset()

    def reset(self):

        self.integral = 0.0

        self.previous_error = None
        self.previous_measurement = None

        self.filtered_derivative = 0.0

    def update(
        self,
        target: float,
        measurement: float,
        dt: float
    ) -> float:

        if dt <= 0:
            raise ValueError("dt must be positive")
        if math.isnan(measurement):
            return 0
        error = target - measurement

        # -----------------------------
        # Derivative
        # -----------------------------

        if self.derivative_on_measurement:

            if self.previous_measurement is None:
                raw_derivative = 0.0
            else:
                raw_derivative = -(
                    measurement - self.previous_measurement
                ) / dt

            self.previous_measurement = measurement

        else:

            if self.previous_error is None:
                raw_derivative = 0.0
            else:
                raw_derivative = (
                    error - self.previous_error
                ) / dt

        self.previous_error = error

        # -----------------------------
        # Low-pass derivative filter
        # -----------------------------

        alpha = dt / (self.derivative_filter_tau + dt)

        self.filtered_derivative += alpha * (
            raw_derivative
            - self.filtered_derivative
        )

        # -----------------------------
        # Integrator
        # -----------------------------

        self.integral += error * dt

        # -----------------------------
        # Unsaturated controller
        # -----------------------------

        unsaturated = (
            self.kp * error
            + self.ki * self.integral
            + self.kd * self.filtered_derivative
        )

        # -----------------------------
        # Saturation
        # -----------------------------

        saturated = unsaturated

        if self.output_min is not None:
            saturated = max(saturated, self.output_min)

        if self.output_max is not None:
            saturated = min(saturated, self.output_max)

        # -----------------------------
        # Back-calculation anti-windup
        # -----------------------------

        if self.ki != 0:

            self.integral += (
                self.anti_windup_gain
                * (saturated - unsaturated)
                / self.ki
            )

        return saturated

# import numpy as np
# import matplotlib.pyplot as plt
# class SimulatedFan:

#     def __init__(
#         self,
#         gain=0.15,          # m/s per PWM %
#         response_time=0.5,  # seconds
#         noise=0.05
#     ):

#         self.gain = gain
#         self.response_time = response_time
#         self.noise = noise

#         self.velocity = 0


#     def update(self, pwm, dt):

#         # Desired velocity from PWM
#         target_velocity = self.gain * pwm

#         # First order fan response
#         self.velocity += (
#             dt / self.response_time
#             * (target_velocity - self.velocity)
#         )

#         # Add probe noise
#         measured = (
#             self.velocity
#             + np.random.normal(0, self.noise)
#         )

#         return measured



# # -----------------------------
# # Simulation settings
# # -----------------------------

# dt = 0.005          # 200 Hz probe
# duration = 30

# target_velocity = 9


# # -----------------------------
# # Controller
# # -----------------------------

# pid = PIDController(
#     kp=2.5,
#     ki=5,
#     kd=1,

#     output_min=-25,
#     output_max=+25,

#     derivative_filter_tau=0.1
# )


# # -----------------------------
# # Feed-forward estimate
# # -----------------------------
# # Assume calibration:
# # velocity = 0.15 * PWM

# feedforward_pwm = target_velocity / 0.16


# # -----------------------------
# # Simulated fan
# # -----------------------------

# fan = SimulatedFan()


# # -----------------------------
# # Run experiment
# # -----------------------------

# time = []
# velocity_history = []
# pwm_history = []


# pwm = feedforward_pwm


# for i in range(int(duration/dt)):

#     t = i * dt


#     # Probe measurement
#     velocity = fan.update(
#         pwm,
#         dt
#     )


#     # PID correction
#     correction = pid.update(
#         target_velocity,
#         velocity,
#         dt
#     )


#     # Feedforward + PID
#     pwm = (
#         feedforward_pwm
#         + correction
#     )


#     # Save
#     time.append(t)
#     velocity_history.append(velocity)
#     pwm_history.append(pwm)



# # -----------------------------
# # Plot results
# # -----------------------------

# plt.figure(figsize=(10,4))

# plt.plot(
#     time,
#     velocity_history,
#     label="Measured velocity"
# )

# plt.axhline(
#     target_velocity,
#     linestyle="--",
#     label="Target"
# )

# plt.xlabel("Time (s)")
# plt.ylabel("Velocity (m/s)")
# plt.legend()
# plt.grid()





# plt.figure(figsize=(10,4))

# plt.plot(
#     time,
#     pwm_history,
#     label="PWM"
# )

# plt.xlabel("Time (s)")
# plt.ylabel("PWM (%)")
# plt.legend()
# plt.grid()

# plt.show()