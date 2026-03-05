import RPi.GPIO as GPIO
import os
import time

fanOn = False
# 添加计数器
turn_on = 0
turn_off = 0
  
# 定义默认温度
defaultTemp = 45
# 定义默认监控间隔
defaultTime = 5

# 获取目标温度
def getWantTemp():
    try:
        with open("TempSet.txt", "r") as setFile:
            wantTemp = int(setFile.read().strip())
    except (FileNotFoundError, IOError, ValueError):
        with open("TempSet.txt", "w") as setFile:
            setFile.write(str(defaultTemp))
        print("没有设置文件，创建一个！")
        wantTemp = defaultTemp
    except Exception as e:
        print(f"文件无法写入！将使用默认值 {defaultTemp}")
        wantTemp = defaultTemp
    return wantTemp

# 获取温控延时
def getWantTime():
    try:
        with open("TimeSet.txt", "r") as setFile:
            wantTime = int(setFile.read().strip())
    except (FileNotFoundError, IOError, ValueError):
        with open("TimeSet.txt", "w") as setFile:
            setFile.write(str(defaultTime))
        print("没有设置文件，创建一个！")
        wantTime = defaultTime
    except Exception as e:
        print(f"文件无法写入！将使用默认值 {defaultTime}")
        wantTime = defaultTime
    return wantTime

# 控制风扇
def controlFan(on):
    global fanOn,turn_on,turn_off
    fanOn = GPIO.input(18)
    print(f"{on} {fanOn}")
    if fanOn != on:
        print(f"尝试将风扇状态更改为: {on}", end='')
        GPIO.output(18, on)
        fanOn = GPIO.input(18)  # 更新fanOn的状态
        if on == True:
            turn_on+=1
        else:
            turn_off+=1
        print(f"，完成，当前{fanOn}")
        

# 获取CPU温度
def getTemp():
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as tempFile:
        temp = int(tempFile.read().strip())
    return temp / 1000

# GPIO设置
def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.OUT)


# 清理GPIO设置
def cleanup_gpio():
    GPIO.cleanup()

# 主程序
def main():
    setup_gpio()
    desired_temp = getWantTemp()
    current_temp =  getTemp()
    sleep_time = getWantTime()
    fanOn = GPIO.input(18)
    print("初始化完成,启用对风扇的自动控制，使用^C进入菜单")
    
    showMenu = False
    try:
       while True:
          if showMenu is not False:
             # 显示菜单
             current_temp =  getTemp()
             os.system('cls' if os.name == 'nt' else 'clear')
             print(f"当前风扇状态: {GPIO.input(18)},当前温度：{getWantTemp()}")
             print(f"开启: {turn_on}次,关闭：{turn_off}次")
             print("\ton:临时打开风扇\n\toff:临时关闭风扇\n\tea:启动对风扇的自动控制\n\t^C:关闭对风扇的自动控制\n\texit/^C:退出程序")
             user_input = input("请输入命令 (on/off/ea/exit): ").strip().lower()
             if user_input == 'on':
                  controlFan(True)
                  print(f"风扇暂时开启，当前温度: {current_temp}℃")
                  time.sleep(3)
                  continue
             elif user_input == 'off':
                  controlFan(False)
                  print(f"风扇暂时关闭，当前温度: {current_temp}℃")
                  time.sleep(3)
                  continue
             elif user_input == 'ea':
                  print("风扇控制已开启。")
             elif user_input == 'exit':
                  print("程序将退出。")
                  break
             else:
                  print("无效的命令，请输入 'start'、'stop' 或 'exit'。")
                  time.sleep(1)
                  continue

            # 如果风扇控制激活，根据温度控制风扇
          while True:
             try:
                # desired_temp = getWantTemp()
                current_temp =  getTemp()
                # sleep_time = getWantTime()
                # fanOn = GPIO.input(18)
                # print("数据更新完成")
                if current_temp is not None:
                  if current_temp > desired_temp:
                          print(f"当前温度：{current_temp}℃ ,设定温度:{desired_temp}℃ ", end='')
                          controlFan(True)
                          print(",风扇开启")
                  elif current_temp < (desired_temp-5):
                          print(f"当前温度：{current_temp}℃ ,设定温度:{desired_temp}℃ ", end='')
                          controlFan(False)
                          print(f",风扇关闭")
                  else:
                          print(f"当前温度：{current_temp}℃ ，在暂缓区间{desired_temp}℃ -{(desired_temp-5)}℃ 内，当前风扇 {GPIO.input(18)}")
                time.sleep(sleep_time)  # 简短的延时，以避免频繁读取温度
             except KeyboardInterrupt:
               print("\n风扇控制已停止。")
               showMenu = 1
               time.sleep(1)
               break

    except KeyboardInterrupt:
        print("\n程序被用户中断。")
        cleanup_gpio()
    

if __name__ == "__main__":
    main()
