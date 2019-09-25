#!/usr/bin/env python3
import random, numpy
import mpu

class Network:
	def __init__(self, bssid, lat, lon):
		self.bssid = bssid
		self.lat = lat
		self.lon = lon
		self.pos = self.lat, self.lon

class NetworkSet:
	def __init__(self):
		self.networks = set()
		self.min_lat = 180
		self.max_lat = -180
		self.min_lon = 180
		self.max_lon = -180

	def add(self, network):
		self.networks.add(network)
		self.min_lat = min(self.min_lat, network.lat)
		self.min_lon = min(self.min_lon, network.lon)
		self.max_lat = max(self.max_lat, network.lat)
		self.max_lon = max(self.max_lon, network.lon)

	def size(self):
		return len(self.networks)

def read_data(filename):
	networks = NetworkSet()
	with open(filename) as fp:
		for line in fp:
			bssid, lat, lon = line.split()
			net = Network(bssid, float(lat), float(lon))
			networks.add(net)
	return networks

def simulate(networks):
	CHANNELS  = [1, 6, 11] + [36, 40, 44]
	CHANNELS += [2, 3, 4, 5, 7, 8, 9, 10, 48, 52, 56, 60, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 148]

	point1 = networks.min_lat, networks.min_lon
	point2 = point1
	while mpu.haversine_distance(point1, point2) <= 0.100:
		point2 = point2[0] + 0.0005, point2[1]
	box_delta = point2[0] - point1[0]

	# 1. Select X% of networks to advertise neighbors
	# 2. Assign a channel to all networks from [1, 6, 11, 36, 40, 44]. TODO: Extra ones if needed.
	# 3. Put the person at a random position & (1) get a network within range (2) one within range and one out of range.
	# 4. See how many channels to scan to get a known networks.
	for x in range(0, 100):
		scans_normal = []
		scans_neighbor = []

		while len(scans_normal) < 500:
			# Select a random location for us
			my_lat = random.uniform(networks.min_lat + 10*box_delta, networks.max_lat - 10*box_delta)
			my_lon = random.uniform(networks.min_lon + 10*box_delta, networks.max_lon - 10*box_delta)
			my_pos = my_lat, my_lon

			# All networks within range
			candidates = []
			for network in networks.networks:
				network.neighbor = False
				if mpu.haversine_distance(network.pos, my_pos) < 0.100:
					candidates.append(network)
			if len(candidates) <= 1:
				continue

			# Let's pick a network we will connect to
			known_network = random.choice(candidates)
			# Another another one to determine it's influence on the scanning,
			# which we later assume is actually out or range.
			known_network2 = random.choice(candidates)
			while known_network2.bssid == known_network.bssid:
				known_network2 = random.choice(candidates)

			# Assign channel and neighbor support with 5% chance
			for network in candidates:
				network.channel = random.choice(CHANNELS)
				network.neighbor = random.randint(1, 100) <= x

			# Now let's see how many networks we need to scan
			num_scans = 0
			to_scan = CHANNELS[:]
			already_scanned = []
			while len(to_scan) > 0:
				curr_channel = to_scan.pop(0)
				num_scans += 1

				# We find the target network
				if known_network.channel == curr_channel:
					break

				# Check if any of the detected networks advertise neighbors
				found = False
				for network in candidates:
					if network.channel == curr_channel and network.neighbor and \
					   mpu.haversine_distance(network.pos, known_network.pos) <= 0.100:
						# Next channel is this one
						to_scan.remove(known_network.channel)
						to_scan = [known_network.channel] + to_scan

					# Other known network might cause extra scan
					if network.channel == curr_channel and network.neighbor and \
					   mpu.haversine_distance(network.pos, known_network2.pos) <= 0.100 and \
					   not known_network2.channel in already_scanned and \
					   curr_channel != known_network2.channel:
						# Next channel is this one
						to_scan.remove(known_network2.channel)
						to_scan = [known_network2.channel] + to_scan

				already_scanned.append(curr_channel)

			#print(x, num_scans, CHANNELS.index(known_network.channel) + 1)
			scans_normal.append(CHANNELS.index(known_network.channel) + 1)
			scans_neighbor.append(num_scans)

		print(x, numpy.average(scans_neighbor), numpy.average(scans_normal))

def main():
	sf = read_data("../openwifi/db/sf.cvs")
	boulder = read_data("../openwifi/db/boulder.cvs")

	simulate(boulder)

if __name__ == "__main__":
	main()

