Our modified `wpa_supplicant` can be found in a [separate repository](https://github.com/vanhoefm/wpa_supplicant-passive).

A [build for the Nexus 5X](https://github.com/vanhoefm/nordsec-passivescan/releases/download/test-build/signed-target-files.zip) that contains our passive scanning modifications can be downloaded from the release tab of this repository.

A [backup of the OpenWiFi dataset](https://github.com/vanhoefm/nordsec-passivescan/releases/download/test-build/db.tar.bz2) can also be downloaded from the release tab.

Overview of files in this repository:
- `android-diffs`: these are patches made to Android.
- `openwifi`: scripts to preprocess the OpenWiFi dataset.
- `scripts`: scripts to measure channel switch times, and to simulate neighbor advertisements.
- `tools`: various scripts and tools to performing the passice scan experiments on the Android phone.
