#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import json
import logging
import signal
import sys
import os

# 读取基础配置
LOG_FILE = "fan_control.log"
CONFIG_FILE = "config.json"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

class PID:
    """
    PID 控制器
    P: 比例控制
    I: 积分控制 (消除静差)
    D: 微分控制 (预测趋势)
    """
    def __init__(self, kp, ki, kd, setpoint):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_time = None
        
        # 积分限幅，防止积分项无限累积 (Anti-windup)
        # 对应占空比 100%
        self.integral_limit = 100.0 / (self.ki if self.ki > 0 else 1.0)

    def update(self, current_value):
        current_time = time.time()
        
        if self.last_time is None:
            self.last_time = current_time
            dt = 0
        else:
            dt = current_time - self.last_time

        error = current_value - self.setpoint
        
        # 只有在有时间流逝时才更新积分和微分
        if dt > 0:
            self.integral += error * dt
            # 积分限幅
            self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
            
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0

        # PID 输出计算
        # 输出值预期为 PWM 增量或直接占空比
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        
        self.prev_error = error
        self.last_time = current_time
        return output

class FanController:
    def __init__(self, config_path):
        self.config_path = config_path
        self.pwm = None
        self.running = False
        self.load_config()
        
    def load_config(self):
        try:
            if not os.path.exists(self.config_path):
                logging.error(f"配置文件 {self.config_path} 不存在")
                sys.exit(1)
                
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logging.info("配置加载成功")
        except Exception as e:
            logging.error(f"加载配置失败: {e}")
            sys.exit(1)

    def setup_hardware(self):
        try:
            # 硬件配置
            hw_conf = self.config['hardware']
            pin = hw_conf['gpio_pin']
            freq = hw_conf['pwm_frequency']
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT)
            
            # 初始化 PWM
            self.pwm = GPIO.PWM(pin, freq)
            self.pwm.start(0)
            logging.info(f"GPIO {pin} 初始化 PID模式，频率 {freq}Hz")
            
        except Exception as e:
            logging.error(f"GPIO 初始化失败: {e}")
            if self.pwm:
                self.pwm.stop()
            GPIO.cleanup()
            sys.exit(1)

    def get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return float(f.read()) / 1000.0
        except:
            return 0.0

    def cleanup(self):
        logging.info("正在清理资源...")
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
        logging.info("程序已退出")

    def run(self):
        self.setup_hardware()
        
        # 获取参数
        target_temp = self.config['temperature']['target_temp']
        min_temp = self.config['temperature']['min_temp_limit']
        max_temp = self.config['temperature']['max_temp_limit']
        check_interval = self.config['temperature']['check_interval']
        
        min_duty = self.config['fan']['min_duty_cycle']
        max_duty = self.config['fan']['max_duty_cycle']
        
        # 初始化 PID
        pid_conf = self.config['pid']
        pid = PID(
            kp=pid_conf['kp'],
            ki=pid_conf['ki'],
            kd=pid_conf['kd'],
            setpoint=target_temp
        )
        
        self.running = True
        logging.info(f"开始温控循环. 目标: {target_temp}°C (区间: {min_temp}-{max_temp}°C)")
        
        try:
            while self.running:
                current_temp = self.get_cpu_temp()
                
                # 安全逻辑：如果超过最大限制，强制全速
                if current_temp >= max_temp:
                    duty_cycle = 100
                    logging.warning(f"温度过高 ({current_temp}°C)! 强制全速")
                    
                # 节能逻辑：如果低于最小限制，完全关闭
                elif current_temp <= min_temp:
                    duty_cycle = 0
                    pid.integral = 0 # 重置积分项，防止积累过大误差
                    
                else:
                    # PID 计算
                    # 只有在温度高于最低阈值且低于最高阈值时才启用PID微调
                    
                    # 基础转速 + PID调整
                    # 我们的目标是把温度控制在 target_temp
                    # 如果当前温度高于目标，输出正值 -> 增加转速
                    
                    pid_out = pid.update(current_temp)
                    
                    # 将 PID 输出转换为 PWM 占空比
                    # 假设我们期望 PID 输出能够覆盖 0-100 的范围
                    # 这里需要根据 Kp 调整，如果 Kp=5, 误差 10度 -> 输出 50%
                    
                    if pid_out < 0: pid_out = 0
                    
                    # 基础占空比 + PID 输出
                    # 如果温度刚到 target，pid_out 接近 0。
                    # 我们可能需要一个基础转速来维持在这个温度，这由 K_i 积分项自动调整
                    
                    duty_cycle = pid_out
                    
                    # 限制范围
                    duty_cycle = max(min_duty, min(max_duty, duty_cycle))

                # 应用 PWM
                if self.pwm:
                    self.pwm.ChangeDutyCycle(duty_cycle)
                
                logging.info(f"Temp: {current_temp:.1f}°C | Target: {target_temp}°C | Fan: {duty_cycle:.1f}%")
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logging.info("接收到中断信号")
        except Exception as e:
            logging.error(f"运行时错误: {e}")
        finally:
            self.cleanup()

if __name__ == "__main__":
    controller = FanController(CONFIG_FILE)
    
    # 注册信号处理
    def signal_handler(sig, frame):
        controller.cleanup()
        sys.exit(0)
        
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    controller.run()
