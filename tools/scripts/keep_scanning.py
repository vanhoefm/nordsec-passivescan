from android import Android
import time
droid = Android()

while True:
    scanStarted = droid.wifiStartScan()
    print(scanStarted)
    time.sleep(0.5)
    ap = droid.wifiGetScanResults()
    aps = ap.result
    print(str(aps))
    time.sleep(3)