from android import Android
import time
droid = Android()

scanStarted = droid.wifiStartScan()
print(scanStarted)