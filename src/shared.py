# Configuration constants
import os
import json
import logging
import sys

# 设置状态文件路径，在Linux上 /dev/shm 是基于内存的，速度快且不写入SD卡
# 如果不是 Linux 或 /dev/shm 不存在，退回到 /tmp
if os.path.exists("/dev/shm"):
    STATUS_FILE = "/dev/shm/fan_status.json"
else:
    STATUS_FILE = "/tmp/fan_status.json"

CONFIG_FILE = "config.json"

# PID Controller
class PID:
    def __init__(self, kp, ki, kd, setpoint, integral_limit=100.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_time = None
        self.integral_limit = integral_limit

    def update(self, current_value, dt):
        error = current_value - self.setpoint
        
        # 积分
        self.integral += error * dt
        # 积分限幅
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        
        # 微分
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0

        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        
        self.prev_error = error
        return output

def load_config(path=CONFIG_FILE):
    if not os.path.exists(path):
        # 默认配置
        return {
            "hardware": {"gpio_pin": 18, "pwm_frequency": 100},
            "temperature": {"target_temp": 55.0, "min_temp_limit": 50.0, "max_temp_limit": 60.0, "check_interval": 1.0},
            "fan": {"min_duty_cycle": 20, "max_duty_cycle": 100},
            "pid": {"kp": 5.0, "ki": 0.2, "kd": 1.0}
        }
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)
