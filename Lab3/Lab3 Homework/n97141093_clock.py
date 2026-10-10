#!/usr/bin/env python3

# Raspberry Pi Python 3 TM1637 quad 7-segment LED display driver examples
from datetime import datetime
from time import sleep
import RPi.GPIO as GPIO

import tm1637

CLK = 6     # 請更改至你實際接線的 GPIO 腳位 (BCM GPIO??)
DIO = 5     # 請更改至你實際接線的 GPIO 腳位 (BCM GPIO??)
DELAY = 0.5

# 初始化 TM1637（只執行一次）
tm = tm1637.TM1637(clk=CLK, dio=DIO)

try:
    while True:
        # 取得 Raspberry Pi 系統時間
        now = datetime.now()

        hour = now.hour
        minute = now.minute
        second = now.second

        # 偶數秒亮，奇數秒滅
        colon = (second % 2 == 0)

        # 顯示 HH:MM
        tm.numbers(hour, minute, colon)

        sleep(0.1)

except KeyboardInterrupt:
    print("程式結束")