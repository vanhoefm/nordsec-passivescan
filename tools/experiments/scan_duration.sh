#!/bin/bash
set -e

EXPERIMENT="duration2"
#EXPERIMENT="specific_ap"
#EXPERIMENT="coverage"

function scan_and_log
{
	for i in $(seq 1 1 5)
	do
		echo "Measuring $1 run $i"

		# Reset Wi-Fi and logcat
		adb shell svc wifi disable
		sleep 2
		adb logcat -c
		adb shell svc wifi enable
		sleep 1

		# Trigger a scan
		adb shell am start -a android.intent.action.MAIN -n com.android.settings/.wifi.WifiSettings
		adb shell input keyevent KEYCODE_WAKEUP

		sleep $2

		# Now log the output
		adb logcat -d > ../../logs/${EXPERIMENT}/scan_$1_run${i}.log
	done
}

# Initialization
adb root
adb remount
adb shell mount -o rw,remount /
adb shell svc wifi disable
sleep 1

# For fair comparison, do active scanning for all strateges
adb push dwell_time_configs/WCNSS_qcom_cfg.orig.ini /system/etc/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini
for STRATEGY in 0 # 1 2 3 4
do
	adb shell settings put global passive_mode_on 0
	adb shell settings put global wifi_scan_strategy $STRATEGY
	scan_and_log "active_strategy${STRATEGY}" 8
done

# Passive scanning for all the strategies
for STRATEGY in 0 1 2 3 # 0 1 2 3 4
do
	adb shell settings put global passive_mode_on 1
	adb shell settings put global wifi_scan_strategy $STRATEGY
	for DWELLTIME in 20 50 100 120 150
	do
		adb push dwell_time_configs/WCNSS_qcom_cfg.$DWELLTIME.ini /system/etc/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini
		scan_and_log "passive_strategy${STRATEGY}_dwell${DWELLTIME}" $(expr 100 \* $DWELLTIME / 1000 + 10)
	done
done

