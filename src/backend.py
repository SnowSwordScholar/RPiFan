import RPi.GPIO as GPIO
import time
import json
import signal
import sys
import os
from .shared import load_config, STATUS_FILE, CONFIG_FILE, PID

# 状态文件路径
# 我们写入一个临时的内存文件，用于与前端通信

class FanController:
    def __init__(self):
        self.config = load_config(CONFIG_FILE)
        self.running = False
        self.pwm = None
        self.last_status_write = 0
        
        # 初始化 PID
        self.target_temp = self.config['temperature']['target_temp']
        kp = self.config['pid']['kp']
        ki = self.config['pid']['ki']
        kd = self.config['pid']['kd']
        self.pid = PID(kp, ki, kd, self.target_temp)
        
        self.setup_gpio()

    def setup_gpio(self):
        try:
            GPIO.setmode(GPIO.BCM)
            pin = self.config['hardware']['gpio_pin']
            freq = self.config['hardware']['pwm_frequency']
            
            GPIO.setup(pin, GPIO.OUT)
            self.pwm = GPIO.PWM(pin, freq)
            self.pwm.start(0)
            
        except Exception as e:
            print(f"[Backend] GPIO Init failed: {e}", file=sys.stderr)
            sys.exit(1)

    def get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return float(f.read()) / 1000.0
        except OSError:
            # 模拟数据用于其他系统测试
            return 45.0 + (time.time() % 20) 

    def update_status(self, temp, duty_cycle, pid_out):
        """写入状态文件供前端读取"""
        current_time = time.time()
        # 控制写入频率 (例如每 0.5s)
        if current_time - self.last_status_write < 0.5:
            return

        status = {
            "timestamp": current_time,
            "current_temp": temp,
            "target_temp": self.target_temp,
            "duty_cycle": duty_cycle,
            "pid_output": pid_out,
            "fan_running": duty_cycle > 0,
            "pid_p": self.pid.kp,
            "pid_i": self.pid.ki,
            "pid_d": self.pid.kd
        }
        
        # 原子写操作：写入临时文件然后移动
        temp_file = STATUS_FILE + ".tmp"
        try:
            with open(temp_file, 'w') as f:
                json.dump(status, f)
            os.replace(temp_file, STATUS_FILE)
            self.last_status_write = current_time
        except Exception as e:
            print(f"[Backend] Failed to update status: {e}", file=sys.stderr)

    def cleanup(self):
        self.running = False
        if self.pwm:
            try: 
                self.pwm.stop()
            except: 
                pass
        try: 
            GPIO.cleanup()
        except: 
            pass
        # 清理状态文件
        if os.path.exists(STATUS_FILE):
            try:
                os.remove(STATUS_FILE)
            except:
                pass

    def run(self):
        self.running = True
        
        min_temp = self.config['temperature']['min_temp_limit']
        max_temp = self.config['temperature']['max_temp_limit']
        check_interval = self.config['temperature']['check_interval']
        
        min_duty = self.config['fan']['min_duty_cycle']
        max_duty = self.config['fan']['max_duty_cycle']
        
        last_pid_time = time.time()
        
        # PID 积分项限制 (Anti-windup)
        # 对应占空比 100%
        # self.pid.integral_limit = 100.0 / (self.pid.ki if self.pid.ki > 0 else 1.0)
        
        try:
            while self.running:
                current_time = time.time()
                dt = current_time - last_pid_time
                if dt < check_interval:
                    time.sleep(0.1)
                    continue

                last_pid_time = current_time
                current_temp = self.get_cpu_temp()
                
                pid_out = 0
                duty_cycle = 0

                # 安全逻辑：如果超过最大限制，强制全速
                if current_temp >= max_temp:
                    duty_cycle = 100
                    # 强制全速时，不更新 PID 可能会导致积分误差累积吗？
                    # 暂时不更新 PID
                    
                # 节能逻辑：如果低于最小限制，完全关闭
                elif current_temp <= min_temp:
                    duty_cycle = 0
                    self.pid.integral = 0 # 重置积分项
                    self.pid.prev_error = 0
                    
                else:
                    # PID 计算
                    pid_out = self.pid.update(current_temp, dt)

                    if pid_out > 0:
                        # 只有当 PID 输出大于 0 时才启动风扇，并由 min_duty 保证最低启动电压
                        duty_cycle = max(min_duty, min(max_duty, pid_out))
                    else:
                        # 温度低于目标且积分项未积累足够正值时，停转
                        duty_cycle = 0
                
                # 设置 PWM
                if self.pwm:
                    self.pwm.ChangeDutyCycle(duty_cycle)
                
                # 更新状态
                self.update_status(current_temp, duty_cycle, pid_out)
                
        except KeyboardInterrupt:
            # 允许手动调试时的优雅退出
            pass
        except Exception as e:
            # Systemd 会捕获 stderr
            print(f"[Backend] Unexpected error: {e}", file=sys.stderr)
        finally:
            self.cleanup()

def main():
    # 注册信号处理
    controller = FanController()
    
    def signal_handler(signum, frame):
        controller.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("[Backend] Fan control service started.", file=sys.stdout)
    controller.run()

if __name__ == "__main__":
    main()
