#!/usr/bin/env python2
import sys, re, datetime, glob, itertools

from bokeh.plotting import figure, output_file, show
import bokeh.palettes
from bokeh.layouts import row
from bokeh.models import Range1d, Span
from bokeh.io import export_svgs
import numpy as np


re_freq = re.compile("Frequency: (\d+) flags")
re_scan_start_incremental = re.compile("Using incremental scan strategy for channel idx (\d+) freq (\d+)")
re_scan_start_priority = re.compile("Using (static|dynamic) priority (2.4 GHz|2.4 \\+ 5 GHz)? ?scan strategy")
re_found_bssid = re.compile("BSS: Add new id \d+ BSSID (..:..:..:..:..:..) SSID (.*) freq (\d+)")

def delta2sec(delta):
	return delta.seconds + delta.microseconds / 1000000.0

def avg(times):
	return sum(times) / len(times)


# ------------------------- DURATION EXPERIMENTS -------------------------

def parse_log_normal(filename):
	scan_started = None
	scan_in_progress = False

	for line in open(filename).readlines():
		line = line.strip()

		# Detect the start of a new individual scan
		if "Using normal scan strategy" in line:
			scan_started = datetime.datetime.strptime(line.split()[1], "%H:%M:%S.%f")
			scan_in_progress = True

		# Detect the end of an individual scan
		if "nl80211: Received scan results" in line:
			scan_ended = datetime.datetime.strptime(line.split()[1], "%H:%M:%S.%f")
			scan_in_progress = False
			return scan_ended - scan_started

	raise Exception("Log {} didn't contain a full normal scan".format(filename))


def parse_log_incremental(filename):
	maxfreq = 0
	scan_started = None
	scan_in_progress = False
	iteration_started = None
	prevfreq = None
	scanning_times = []

	for line in open(filename).readlines():
		line = line.strip()

		# Track the maximum frequency to know when incremental scanning has ended
		m = re_freq.search(line)
		if m and not "ignored" in line:
			freq = int(m.group(1))
			if freq > maxfreq: maxfreq = freq

		# Detect the start of a new individual scan
		m = re_scan_start_incremental.search(line)
		if m:
			iteration_started = datetime.datetime.strptime(line.split()[1], "%H:%M:%S.%f")
			prevfreq = int(m.group(2))
			if scan_started is None: scan_started = iteration_started
			scan_in_progress = True

		# Detect the end of an individual scan
		if scan_in_progress and "nl80211: Received scan results" in line:
			iteration_ended = datetime.datetime.strptime(line.split()[1], "%H:%M:%S.%f")
			scanning_times.append(iteration_ended - iteration_started)
			scan_in_progress = False

			# Was this the last channel that had to be scanned?
			if prevfreq == maxfreq:
				print filename, scan_started, iteration_ended
				return sum(scanning_times, datetime.timedelta()), iteration_ended - scan_started

	raise Exception("Log {} didn't contain a full incremental scan".format(filename))


def parse_log_priority(filename):
	scan_started = None
	scan_in_progress = False
	scan_time_prior = None
	priority_scan_done = 0

	for line in open(filename).readlines():
		line = line.strip()

		# Detect the start of a new individual scan
		m = re_scan_start_priority.search(line)
		if m:
			scan_started = datetime.datetime.strptime(line.split()[1], "%H:%M:%S.%f")
			scan_in_progress = True

		# Detect the end of an individual scan
		if "nl80211: Received scan results" in line:
			scan_ended = datetime.datetime.strptime(line.split()[1], "%H:%M:%S.%f")
			scan_time = scan_ended - scan_started

			if priority_scan_done > 1:
				return scan_time_prior, scan_time_prior + scan_time

			scan_time_prior = scan_time
			scan_in_progress = False
			priority_scan_done += 1

	raise Exception("Log {} didn't contain a full priority scan".format(filename))


def get_active_normal(experiment, strategy):
	filename = "../../../logs/{}/scan_active_strategy{}_run*.log".format(experiment, strategy)
	return [delta2sec(parse_log_normal(f)) for f in glob.glob(filename)]

def get_passive(experiment, strategy, dwell, totaltime=False):
	filename = "../../../logs/{}/scan_passive_strategy{}_dwell{}_run*.log".format(experiment, strategy, dwell)
	if strategy == 0:
		return [delta2sec(parse_log_normal(f)) for f in glob.glob(filename)]
	elif strategy == 1:
		results = [parse_log_incremental(f) for f in glob.glob(filename)]
		return map(lambda n: delta2sec(n[1] if totaltime else n[0]), results)
	else:
		results = [parse_log_priority(f) for f in glob.glob(filename)]
		return map(lambda n: delta2sec(n[1] if totaltime else n[0]), results)


def plot_duration_normal_incremental():
	dwelltimes = [20, 50, 100, 120, 150]
	active_normal = avg(get_active_normal("duration", 0))
	passive_normal = [avg(get_passive("duration", 0, dwell)) for dwell in dwelltimes]
	passive_incremental_scan = [avg(get_passive("duration", 1, dwell)) for dwell in dwelltimes]
	passive_incremental_total = [avg(get_passive("duration", 1, dwell, totaltime=True)) for dwell in dwelltimes]

	print "Overhead incremental scan:", avg([float(t1 - t2) / t1 for t1, t2 in zip(passive_incremental_total, passive_normal)])

	# create a new plot with a title and axis labels
	colors = bokeh.palettes.Greens8
	p = figure(title="", x_axis_label='Dwell time (ms)', y_axis_label='Scan duration (s)',
		plot_width=490, plot_height=340)
	p.output_backend = "svg"

	# Plot passive scanning experiment lines
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], passive_incremental_total + [0, 0], color=colors[6], line_width=2)
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], passive_incremental_scan + [0, 0], color=colors[5], line_width=2)
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], passive_normal + [0, 0], color=colors[4], line_width=2)

	p.line(dwelltimes, passive_normal, line_width=2, color=colors[0])
	p.square(dwelltimes, passive_normal, color=colors[0], legend='Standard passive scan', size=6)

	p.line(dwelltimes, passive_incremental_scan, line_width=2, color=colors[2])
	p.circle(dwelltimes, passive_incremental_scan, color=colors[2], legend='Incremental scan', size=6)

	p.line(dwelltimes, passive_incremental_total, line_width=2, color=colors[4])
	p.triangle(dwelltimes, passive_incremental_total, color=colors[4], legend='Incremental scan (with overhead)', size=8)

	# Comparison with active scanning
	p.line(dwelltimes, active_normal, line_width=2, color=colors[2], legend="Default active scan")

	p.legend.location = 'top_left'
	p.y_range = Range1d(0, 7)

	return p


def plot_duration_static_priority():
	dwelltimes = [20, 50, 100, 120, 150]
	active_normal = avg(get_active_normal("duration", 0))
	passive_static_prior2 = [avg(get_passive("duration", 2, dwell)) for dwell in dwelltimes]
	passive_static_full2 = [avg(get_passive("duration", 2, dwell, totaltime=True)) for dwell in dwelltimes]
	passive_static_prior25 = [avg(get_passive("duration", 3, dwell)) for dwell in dwelltimes]
	passive_static_full25 = [avg(get_passive("duration", 3, dwell, totaltime=True)) for dwell in dwelltimes]

	print "Percentage 2 GHz  :", avg([float(t1 - t2) / t1 for t1, t2 in zip(passive_static_full2, passive_static_prior2)])
	print "Percentage 2+5 GHz:", avg([float(t1 - t2) / t1 for t1, t2 in zip(passive_static_full25, passive_static_prior25)])

	# create a new plot with a title and axis labels
	colors = bokeh.palettes.Greens8
	p = figure(title="", x_axis_label='Dwell time (ms)', y_axis_label='Scan duration (s)',
		plot_width=470, plot_height=335)
	p.output_backend = "svg"

	# Plot passive scanning experiment lines
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], passive_static_full25 + [0, 0], color=colors[6], line_width=2)
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], passive_static_prior25 + [0, 0], color=colors[5], line_width=2)
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], passive_static_prior2 + [0, 0], color=colors[4], line_width=2)

	p.line(dwelltimes, passive_static_prior2, line_width=2, color=colors[0])
	p.square(dwelltimes, passive_static_prior2, color=colors[0], legend='Priority scan 2.4 GHz', size=6)

	p.line(dwelltimes, passive_static_prior25, line_width=2, color=colors[2])
	p.circle(dwelltimes, passive_static_prior25, color=colors[2], legend='Priority scan 2.4 + 5 GHz', size=6)

	p.line(dwelltimes, passive_static_full25, line_width=2, color=colors[4])
	p.triangle(dwelltimes, passive_static_full25, color=colors[4], legend='Full scan time', size=8)

	# Comparison with active scanning
	p.line(dwelltimes, active_normal, line_width=2, color=colors[2], legend="Default active scan")

	p.legend.location = 'top_left'
	p.y_range = Range1d(0, 6.2)

	return p


# ------------------------- DISCOVERY RATES EXPERIMENTS -------------------------


class Network():
	def __init__(self, bssid, freq=None):
		self.bssid = bssid
		self.freq = freq

	def __hash__(self):
		return len(self.bssid) + self.freq

	def __eq__(self, other):
		return self.bssid == other.bssid and self.freq == other.freq

	def __repr__(self):
		return "Network({}, {})".format(self.bssid, self.freq)


def parse_log_networks(filename):
	networks = set()
	scan_failed = False
	time_prev_scan = None

	for line in open(filename).readlines():
		line = line.strip()

		if "Scan requested (ret=0)" in line:
			time_scan = datetime.datetime.strptime(line.split()[1], "%H:%M:%S.%f")
			if time_prev_scan:
				if (time_scan - time_prev_scan).seconds >= 3:
					return networks

			time_prev_scan = time_scan

		m = re_found_bssid.search(line)
		if m:
			networks.add(Network(m.group(1), int(m.group(3))))

		if "Failed to start single scan" in line:
			scan_failed = True

	if scan_failed and len(networks) == 0:
		return None
	return networks


def plot_discovery(location):
	# FIXME: Only consider the networks that were present in at least X runs?
	totalnetworks = set()
	for filename in glob.glob("../../../logs/{}/*.log".format(location)):
		networks = parse_log_networks(filename)
		if networks: totalnetworks |= networks
	total = float(len(totalnetworks))
	print len(totalnetworks)

	discovery_rate = []
	for filename in glob.glob("../../../logs/{}/scan_active_strategy0_run*.log".format(location)):
		networks = parse_log_networks(filename)
		if not networks: continue
		discovery_rate.append(len(networks) / total)
	rate_active = avg(discovery_rate)

	rate_passive = []
	rate_passive_prior2 = []
	rate_passive_prior25 = []
	for dwell in [20, 50, 100, 120, 150]:
		discovery_rate = []
		discovery_rate_prior2 = []
		discovery_rate_prior25 = []
		for filename in glob.glob("../../../logs/{}/scan_passive_strategy*_dwell{}_run*.log".format(location, dwell)):
			# This should not include incremental scans (parse_log_networks cannot extract only the first scan)
			assert not "strategy1" in filename

			networks = parse_log_networks(filename)
			if not networks: continue
			discovery_rate.append(len(networks) / total)
			priornetworks2  = [network for network in networks if network.freq in [2412, 2437, 2462]]
			priornetworks25 = [network for network in networks if network.freq in [2412, 2437, 2462, 5180, 5220, 5200]]
			discovery_rate_prior2.append(len(priornetworks2) / total)
			discovery_rate_prior25.append(len(priornetworks25) / total)
		rate_passive.append(avg(discovery_rate))
		rate_passive_prior2.append(avg(discovery_rate_prior2))
		rate_passive_prior25.append(avg(discovery_rate_prior25))

	print location, "-> Average discovery 2.4:", avg([prior / full for prior, full in zip(rate_passive_prior2, rate_passive)])
	print location, "-> Average discovery 2.4 + 5:", avg([prior / full for prior, full in zip(rate_passive_prior25, rate_passive)])

	dwelltimes = [20, 50, 100, 120, 150]

	# create a new plot with a title and axis labels
	colors = bokeh.palettes.Greens8
	p = figure(title="", x_axis_label='Dwell time (ms)', y_axis_label='AP discovery rate',
		plot_width=470, plot_height=330)
	p.output_backend = "svg"

	# Plot passive scanning experiment lines
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], rate_passive + [0, 0], color=colors[6], line_width=2)
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], rate_passive_prior25 + [0, 0], color=colors[5], line_width=2)
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], rate_passive_prior2 + [0, 0], color=colors[4], line_width=2)

	p.line(dwelltimes, rate_passive_prior2, line_width=2, color=colors[0])
	p.square(dwelltimes, rate_passive_prior2, color=colors[0], legend='Priority scan 2.4 GHz', size=6)

	p.line(dwelltimes, rate_passive_prior25, line_width=2, color=colors[2])
	p.circle(dwelltimes, rate_passive_prior25, color=colors[2], legend='Priority scan 2.4 + 5 GHz', size=6)

	p.line(dwelltimes, rate_passive, line_width=2, color=colors[4])
	p.triangle(dwelltimes, rate_passive, color=colors[4], legend='Full scan', size=8)

	# Comparison with active scanning
	p.line(dwelltimes, rate_active, line_width=2, color=colors[2], legend="Default active scan")

	p.legend.location = 'top_left'
	if location == "london":
		p.y_range = Range1d(0, 0.53)
	elif location == "office":
		p.y_range = Range1d(0, 0.85)

	return p

# ------------------------- TIME-TO-CONNECT EXPERIMENTS -------------------------

def parse_log_ttc(filename):
	scan_started = None
	scan_in_progress = False

	for line in open(filename).readlines():
		line = line.strip()

		# Detect the start of a new individual scan
		if "Scan requested (ret=0)" in line and not scan_in_progress:
			scan_started = datetime.datetime.strptime(line.split()[1], "%H:%M:%S.%f")
			scan_in_progress = True

		# Detect the end of an individual scan
		if "c4:e9:84:db:fb:7b" in line:
			network_found = datetime.datetime.strptime(line.split()[1], "%H:%M:%S.%f")
			scan_in_progress = False
			return network_found - scan_started

	print "Warning: log {} didn't detect the network! Assuming it would be detected in 9 seconds.".format(filename)
	return datetime.timedelta(seconds=9)

def get_ttc_active(strategy):
	# TODO: Remove duration from all the log files
	filename = "../../../logs/specific_ap/scan_active_strategy{}_run*.log".format(strategy)
	return [delta2sec(parse_log_ttc(f)) for f in glob.glob(filename)]

def get_ttc_passive(strategy, dwell):
	# TODO: Remove duration from all the log files
	filename = "../../../logs/specific_ap/scan_passive_strategy{}_dwell{}_run*.log".format(strategy, dwell)
	return [delta2sec(parse_log_ttc(f)) for f in glob.glob(filename)]



def plot_ttc_active_dynamic():
	# https://bokeh.pydata.org/en/latest/docs/reference/plotting.html#bokeh.plotting.figure.Figure.vbar
	# https://bokeh.pydata.org/en/latest/docs/reference/models/glyphs/vbar.html
	ttc_active = get_ttc_active(4)
	hist, bin_edges = np.histogram(ttc_active, bins=30)

	output_file("bars.html")

	p = figure(plot_width=700, plot_height=400, title="", x_axis_label='Time-to-connect (s)', y_axis_label='No. of cases')
	p.output_backend = "svg"

	# FIXME: Use max(ttc_active) - min(ttc_active) to properly center the bars
	p.vbar(x=bin_edges[:-1], top=hist, width=0.0008, fill_color="#F45666", line_width=1, line_color="black")

	p.xgrid.grid_line_color = None
	p.y_range.start = 0

	show(p)

def plot_ttc_passive_dynamic(dwell=120):
	numbars = 20

	# https://bokeh.pydata.org/en/latest/docs/reference/plotting.html#bokeh.plotting.figure.Figure.vbar
	# https://bokeh.pydata.org/en/latest/docs/reference/models/glyphs/vbar.html
	ttc_passive = get_ttc_passive(4, dwell)
	hist, bin_edges = np.histogram(ttc_passive, bins=numbars)
	print hist

	output_file("bars.html")

	p = figure(plot_width=410, plot_height=290, title="", x_axis_label='Time-to-connect (s)', y_axis_label='No. of cases')
	p.output_backend = "svg"
	p.xgrid.grid_line_color = None
	p.y_range.start = 0
	if dwell == 100:
		p.x_range = Range1d(0, 10)
		bar_width = (p.x_range.start - p.x_range.end) / float(numbars)
	else:
		p.x_range = Range1d(min(ttc_passive) - 0.002, max(ttc_passive) + 0.002)
		bar_width = (p.x_range.start - p.x_range.end) / float(numbars) / 1.5

	# FIXME: Use max(ttc_active) - min(ttc_active) to properly center the bars
	p.vbar(x=bin_edges[1:], top=hist, width=bar_width, fill_color="#F45666", line_width=1, line_color="black")
	return p

def plot_dynamic_discovery():
	# Re-draw results of Frederik in SVG format
	dwelltimes = [20, 50, 100, 120, 150]
	rate_active = 1
	rate_dynamic = [0.17, 0.44, 0.94, 1, 1]

	# create a new plot with a title and axis labels
	colors = bokeh.palettes.Greens8
	p = figure(title="", x_axis_label='Dwell time (ms)', y_axis_label='Specific AP discovery rate',
		plot_width=410, plot_height=290) # 700, 500
	p.output_backend = "svg"

	# Plot passive scanning experiment lines
	p.patch(dwelltimes + [dwelltimes[-1], dwelltimes[0]], rate_dynamic + [0, 0], color=colors[5], line_width=2)

	p.line(dwelltimes, rate_dynamic, line_width=2, color=colors[2])
	p.circle(dwelltimes, rate_dynamic, color=colors[2], size=6)

	# Comparison with active scanning
	p.line(dwelltimes, rate_active, line_width=2, color="black", line_dash="dashed")

	#p.legend.location = 'top_left'
	p.y_range = Range1d(0, 1.05)

	return p

# ------------------------- MAIN -------------------------

def main():
	# output to static HTML file
	output_file("plots.html")
	plots = []
	#plots.append(plot_dynamic_discovery())
	#plots.append(plot_ttc_passive_dynamic(dwell=120))
	#plots.append(plot_ttc_passive_dynamic(dwell=100))
	#plots.append(plot_discovery("office"))
	#plots.append(plot_discovery("london"))
	#plots.append(plot_duration_normal_incremental())
	plots.append(plot_duration_static_priority())
	show(row(plots))


if __name__ == "__main__":
	main()

