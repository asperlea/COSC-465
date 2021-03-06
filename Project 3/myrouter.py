#!/usr/bin/env python

'''
Basic IPv4 router (static routing) in Python, stage 1.
Authors: Curtis Mahoney * Adriana Sperlea
Date: 2/20/2014
'''

import sys
import os
import os.path
sys.path.append(os.path.join(os.environ['HOME'],'pox'))
sys.path.append(os.path.join(os.getcwd(),'pox'))
import pox.lib.packet as pktlib
from pox.lib.packet import ethernet,ETHER_BROADCAST,IP_ANY
from pox.lib.packet import arp
from pox.lib.addresses import EthAddr,IPAddr
from srpy_common import log_info, log_debug, log_warn, SrpyShutdown, SrpyNoPackets, debugger

class Router(object):
	def __init__(self, net):
		self.net = net
		self.ip_to_ether = {} #Empty dict to store mappings
		self.my_interfaces = {}
		
		for intf in net.interfaces():
			self.my_interfaces[intf.ipaddr] = intf.ethaddr

	def router_main(self):	
		while True:
			try:
				dev,ts,pkt = self.net.recv_packet(timeout=1.0)
				payload = pkt.payload
				
				if pkt.find("arp"): #Is an ARP
					src_ip = payload.protosrc
					dst_ip = payload.protodst
					src_eth = payload.hwsrc
					#no dst
					
					if not(src_ip in self.ip_to_ether): #For later use
						self.ip_to_ether[src_ip] = src_eth
					
					hwdst = None
					if dst_ip in self.my_interfaces: #lookup eth
						hwdst = self.my_interfaces[dst_ip]
							
					if hwdst != None: #if we have that ip
						arp_rep = arp() #Build up packet
						
						arp_rep.opcode = arp.REPLY
						arp_rep.protosrc = dst_ip
						arp_rep.protodst = src_ip
						arp_rep.hwsrc = hwdst #Matching ether
						arp_rep.hwdst = src_eth
						
						ether = ethernet() #wrap in ether
						ether.type = ether.ARP_TYPE
						ether.set_payload(arp_rep)
						ether.src = hwdst
						ether.dst = src_eth
						
						self.net.send_packet(dev, ether) #send it off
			except SrpyNoPackets:
				# log_debug("Timeout waiting for packets")
				continue
			except SrpyShutdown:
				return


def srpy_main(net):
	'''
	Main entry point for router.  Just create Router
	object and get it going.
	'''
	r = Router(net)
	r.router_main()
	net.shutdown()
	
