from android import Android
import datetime
import time

a = Android()

a.batteryStartMonitoring()
time.sleep(2)

print(a.readBatteryData())