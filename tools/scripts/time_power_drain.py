from android import Android
import subprocess
import datetime
import time

limit=90

a = Android()

print("starting monitor funcs")
a.batteryStartMonitoring()
time.sleep(1)
print("monitoring engaged, waiting for battery level to be full")
while not a.batteryGetStatus().result == 5:
	time.sleep(0.5)
print("battery full, unplug now")
while a.batteryGetStatus().result == 5:
	time.sleep(0.1)

print(subprocess.check_output(["dumpsys","batterystats","--reset"]))

print("Time: " + str(datetime.datetime.now()))
print("Battery level: " + str(a.batteryGetLevel().result))

counter = 1
while a.batteryGetLevel().result > limit:
	time.sleep(1)
	counter = counter + 1
	if(counter>10):
		counter = 0
		with open("/sdcard/voltages.txt", "a") as file:
			file.write(str(a.batteryGetVoltage().result) + "\n")

print("Time: " + str(datetime.datetime.now()))
print("Battery level: " + str(a.batteryGetLevel().result))

a.batteryStopMonitoring()
print("monitoring disengaged")

with open("/sdcard/dumpsys.txt", "w") as file:
	file.write(subprocess.check_output(["dumpsys","batterystats"]))

with open("/sdcard/test.txt", "a") as file:
	file.write("testfinaal\n")

while True:
	a.vibrate(200)
	time.sleep(1)
