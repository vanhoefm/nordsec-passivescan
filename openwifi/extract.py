#!/usr/bin/env python3

def main():
	sf = []
	boulder = []
	la = []

	with open("db/db.csv") as fp:
		# Read all the APs
		for line in fp:
			bssid, lat, lon = line.split()
			if bssid == "bssid": continue

			# Two locations: SF and Boulder
			if 37.78 <= float(lat) <= 37.81 and -122.41 <= float(lon) <= -122.39:
				sf.append(line)
			elif 39.99 <= float(lat) <= 40.02 and -105.28 <= float(lon) <= -105.25:
				boulder.append(line)
			elif 34.00 <= float(lat) <= 34.10 and -118.30 <= float(lon) <= -118.20:
				la.append(line)

	with open("db/sf.cvs", "w") as fp:
		fp.write("".join(sf))
	with open("db/boulder.cvs", "w") as fp:
		fp.write("".join(boulder))
	with open("db/la.cvs", "w") as fp:
		fp.write("".join(la))

if __name__ == "__main__":
	main()

