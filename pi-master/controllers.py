# Collection of controllers for various tasks
#
# Retains state of last observation as well as setpoint etc
# Each update should provide a new observation and returns a new setting to apply
# Observations and outputs assume to be ints but internally uses floats

class HEADING_PID:
    """
        Simple PID controller for heading control, works on heading range of 0-255 to match sensor
        Handles wrap-around at 0/360
        Initialize to current heading to avoid large initial changes
        Update returns the delta change required
    """
    def __init__(self, kp:float = 1.0, ki:float = 0.1, kd:float = 0.05):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = 0
        self.last_setting = 0
        self.last_value = 0
        self.integral = 0
        self.last_error = 0

    def set_target(self, target: int):
        self.setpoint = target
    
    def set_current(self, current):
        self.last_value = current

    def last_error(self):
        return self.setpoint - self.last_value

    def limit(self, value: int) -> int:
        if value > 128:
            return 128
        elif value < -127:
            return -127
        return value
    
    def delta_norm(self, delta: int) -> int:
        if delta > 128:
            return delta - 256
        elif delta < -127:
            return delta + 256
        return delta

    def update(self, current_value: int) -> int:
        error = self.delta_norm(self.setpoint - current_value)
        self.integral = self.limit(self.integral + error)
        # Use derivative kick trick: http://brettbeauregard.com/blog/2011/04/improving-the-beginners-pid-derivative-kick/
        derivative = -(current_value - self.last_value)
        delta = self.delta_norm((self.kp * error) + (self.ki * self.integral) + (self.kd * derivative))
        output = self.limit(round(self.last_setting + delta))
        # print(f"PID: SP={self.setpoint}, CV={current_value}, Err={error}, Int={self.integral}, Der={derivative}, Out={output}, Delta={delta}")
        self.last_setting = output
        self.last_value = current_value
        self.last_error = error
        return round(delta)
