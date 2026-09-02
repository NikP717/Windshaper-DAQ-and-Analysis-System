import math
import numpy as np

class PIDController():
    """Class which containns all the required logic of a standard PID Control 
    with anti-wind up, derivate filtering, saturation handling, error handling and dynamic dt handling."""
    def __init__(self, kp, ki, kd, lim=(-20,20)) -> None:
        """Initialises gains and resets any prior measurements and sets limits."""
        self.kp = kp
        self.ki = ki
        self.kd = kd
        # Output limits
        self.output_min = lim[0]
        self.output_max = lim[1]

        # Anti-windup
        self.anti_windup_gain = 0.2

        # Derivative filter time constant (seconds)
        self.cutoff_fq = 5 # Hz
        self.derivative_filter_tau: float = 1/(self.cutoff_fq*(2*math.pi))

        # Derivative on measurement avoids setpoint kick
        self.derivative_on_measurement = True
        self.reset()

    def reset(self) -> None:
        """Function which refreshers all measurements and integral accumulation term."""

        self.integral = 0.0

        self.previous_error = None
        self.previous_measurement = None

        self.filtered_derivative = 0.0

    def update(self, target: float, measurement: float, dt: float) -> float:
        """Function which creates a step change in the PID response across a change of time dt."""
        if dt <= 0:
            return 0
        if math.isnan(measurement):
            measurement = 0
        
        error = target - measurement

        if self.derivative_on_measurement:
            if self.previous_measurement is None:
                raw_derivative = 0.0
            else:
                raw_derivative = -(measurement - self.previous_measurement) / dt

            self.previous_measurement = measurement

        else:
            if self.previous_error is None:
                raw_derivative = 0.0
            else:
                raw_derivative = (error - self.previous_error) / dt

        self.previous_error = error

        # Derivative filter
        alpha = dt / (self.derivative_filter_tau + dt)

        self.filtered_derivative += alpha * (raw_derivative- self.filtered_derivative)

        # Integrator
        self.integral += error * dt

        if self.ki != 0:
            integral_limit = 10/self.ki
        else:
            integral_limit = 0
        self.integral = np.clip(self.integral,-integral_limit,integral_limit)

        # Unsaturated controller
        unsaturated = (self.kp * error+ self.ki * self.integral + self.kd * self.filtered_derivative)

        # Saturation
        saturated = unsaturated

        if self.output_min is not None:
            saturated = max(saturated, self.output_min)

        if self.output_max is not None:
            saturated = min(saturated, self.output_max)

        # Back-calculation anti-windup
        if self.ki != 0:
            self.integral += (self.anti_windup_gain * (saturated - unsaturated)/ self.ki)
        return saturated
