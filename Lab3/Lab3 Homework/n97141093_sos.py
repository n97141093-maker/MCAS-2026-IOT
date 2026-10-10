
import RPi.GPIO as GPIO
import time

LED = 37       # BOARD Pin 37 = GPIO26
BUZZER = 16    # BOARD Pin 16 = GPIO23
freq = 523 

GPIO.setmode(GPIO.BOARD)

GPIO.setup(LED, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)

voice = GPIO.PWM(BUZZER, freq)

# 摩斯密碼時間設定
SHORT = 0.3
LONG = SHORT * 3
GAP = SHORT

def signal(duration):
    # LED 亮、蜂鳴器響
    GPIO.output(LED, GPIO.HIGH)
    voice.start(50)   # duty 50%，發聲

    time.sleep(duration)

    # LED 滅、蜂鳴器停止
    GPIO.output(LED, GPIO.LOW)
    voice.stop()      # 停止發聲

    time.sleep(GAP)

try:
    while True:
        # S：三短
        for i in range(3):
            signal(SHORT)

        time.sleep(SHORT * 2)

        # O：三長
        for i in range(3):
            signal(LONG)

        time.sleep(SHORT * 2)

        # S：三短
        for i in range(3):
            signal(SHORT)

        # SOS 結束，等待下一次
        time.sleep(SHORT * 6)

except KeyboardInterrupt:
    print("程式結束")

finally:
    GPIO.cleanup()
