#!/usr/bin/env python3
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *
import select

def swap64(i):
    return struct.unpack("<Q", struct.pack(">Q", i))[0]

def get_tlv_value(p, type):
	if not Dot11Elt in p: return None
	el = p[Dot11Elt]
	while isinstance(el, Dot11Elt):
		if el.ID == type:
			return el.info
		el = el.payload
	return None

class ProbeInfo:
	def __init__(self, addr, hwtime, seqnum, channel):
		self.addr = addr
		self.hwtime = hwtime
		self.seqnum = seqnum
		self.channel = channel
def main():
	if len(sys.argv) != 2:
		print("Usage: %s mac_address" % sys.argv[0])
		quit(1)

	stamac = sys.argv[1]
	sock = L2Socket(type=ETH_P_ALL, iface="wlp2s0")
	prevprobe = None

	fp = open("deltas_%s.cvs" % stamac, "a")

	num_samples = 0
	print("Listening for probe requests from", stamac)
	while num_samples < 100:
		sel = select.select([sock], [], [], 1)

		# Receive valid Dot11 packets
		p = sock.recv(MTU)
		if p == None or not (Dot11 in p or Dot11FCS in p): continue

		# We only care about probe requests from our STA
		if not Dot11ProbeReq in p or p.addr2 != stamac: continue

		# Get the hardware Rx time and the sequence number
		hwtime = swap64(p.mac_timestamp)
		seqnum = p.SC >> 4

		# Get the scanned channel from the information elements
		channel = get_tlv_value(p, 3)
		if channel is None: continue
		channel = struct.unpack("<B", channel)[0]

		# Save all the info together
		currprobe = ProbeInfo(p.addr2, hwtime, seqnum, channel)
		print("[%d] %s seqnum=%d channel=%d" % (hwtime, p.addr2, seqnum, channel))

		# If the previous frame was also a probe, calculate the difference ..
		if prevprobe and prevprobe.channel + 1 == currprobe.channel and prevprobe.seqnum + 1 == currprobe.seqnum:
			num_samples += 1
			delta = currprobe.hwtime - prevprobe.hwtime
			print(">>> %s: %d (%d measurements)" % (stamac, delta, num_samples))
			fp.write("%d\n" % delta)

		# Mark the new probe as the previous one
		prevprobe = currprobe

	fp.close()

if __name__ == "__main__":
	main()

