#!/usr/bin/env python

'''
Basic IPv4 router (static routing) in Python, stage 2.
-Builds on (heavily modified) code from stage 1
Authors: Curtis Mahoney & Adriana Sperlea
Date: 3/06/2014
'''

import sys
import os
import os.path
from sets import Set
sys.path.append(os.path.join(os.environ['HOME'],'pox'))
sys.path.append(os.path.join(os.getcwd(),'pox'))
import pox.lib.packet as pktlib
from pox.lib.packet import ethernet,ETHER_BROADCAST,IP_ANY
from pox.lib.packet import arp
from pox.lib.addresses import EthAddr,IPAddr,netmask_to_cidr
from srpy_common import log_info, log_debug, log_warn, SrpyShutdown, SrpyNoPackets, debugger
import time

class Router(object):
	def __init__(self, net):
		self.net = net
		
		self.ip_to_ether = {} #Empty dict to store mappings
		self.my_interfaces = Set() #Set of ip's for this router's interfaces
		self.forwardingTable = {}
		self.nameMap = {} #Maps from intf names to ip and eth addresses
		
		self.buildMappings()		
	
	def makeReply(self, dst_ip, src_ip, hwdst, src_eth):
		'''
		Creates an ARP reply packet given IP source and destination, Ethernet source and destination
		'''

		arp_rep = arp() #Build up packet
		
		arp_rep.opcode = arp.REPLY
		arp_rep.protosrc = dst_ip
		arp_rep.protodst = src_ip
		arp_rep.hwsrc = hwdst #Matching ethernet asked for in initial request
		arp_rep.hwdst = src_eth
			
		ether = ethernet() #wrap in ether
		ether.type = ether.ARP_TYPE
		ether.set_payload(arp_rep)
		ether.src = hwdst
		ether.dst = src_eth

		return ether

	def makeRequest(self, dst_ip, src_ip, src_eth):
		'''
		Creates an ARP request packet
		-Of same structure as makeReply, but distinct enough that it's worth having
			different functions that lay it all out
		'''

		arp_req = arp()

		arp_req.opcode = arp.REQUEST
		arp_req.protosrc = src_ip
		arp_req.protodst = dst_ip
		arp_req.hwsrc = src_eth
		arp_req.hwdst = ETHER_BROADCAST

		ether = ethernet() #wrap in ether
		ether.type = ether.ARP_TYPE
		ether.set_payload(arp_req)
		ether.src = src_eth
		ether.dst = ETHER_BROADCAST
		
		return ether
		
		
	def buildMappings(self):
		'''
		Creates a Forwarding Table for the router, as well as establishing mappings from
		names to eth and ip, storing a list of ip's associated with my interfaces, and
		initializing the table of mappings from ip to eth addresses
		
		Addresses in forwarding table are stored in binary for easy bitwise operations
		'''
		
		#Obtain routes from net.interfaces
		for intf in self.net.interfaces():
			prefix = intf.ipaddr.toUnsigned() & intf.netmask.toUnsigned() # network prefix
			mask = intf.netmask # network mask
			nexthop = None # next hop
			name = intf.name # interface name

			self.forwardingTable[prefix] = tuple([mask, nexthop, name])
			
			self.nameMap[name] = (intf.ethaddr, intf.ipaddr)
			self.my_interfaces.add(intf.ipaddr)
			self.ip_to_ether[intf.ipaddr] = intf.ethaddr

		#Obtain routes from forwarding_table.txt
		forTable = open("forwarding_table.txt", "r")
		for line in forTable:
			parsedLine = line.split(" ")
			prefix = IPAddr(parsedLine[0]).toUnsigned() # network prefix
			mask = IPAddr(parsedLine[1]) # network mask
			nexthop = IPAddr(parsedLine[2]) # next hop
			name = parsedLine[3][0:-1] # interface name
					   
			self.forwardingTable[prefix] = tuple([mask, nexthop, name])
	   
	def matchPrefix(self, dstip):
		best_prefix = None
		best_match = -1
		for prefix in self.forwardingTable:
			netmask = self.forwardingTable[prefix][0] # 0 is the netmask
			if prefix == (dstip.toUnsigned() & netmask.toUnsigned()):
				if best_match ==-1 or best_match < netmask_to_cidr(netmask):
					best_prefix = prefix
					best_match = netmask_to_cidr(netmask)
					
		if best_prefix == None: #No matches at all
			return None
			
		return self.forwardingTable[best_prefix] #Index 1 is the nexthop
		
	def examineStalled(self, arp_ip):
		keys = arp_ip.keys() #Can/will lose keys during iteration
		for dst in keys:
			stalled = arp_ip.pop(dst)
			
			if dst in self.ip_to_ether: #We've since figured this one out
				dst_eth = self.ip_to_ether[dst]
				
				for ether_pkt in stalled.getList(): #Send out all the waiting packets
					ether_pkt.dst = dst_eth
					self.net.send_packet(stalled.intf_name, ether_pkt)
			else:
				difference = time.time() - stalled.start_time
			
				if difference/stalled.tries > 1:
					if stalled.tries >=5: #Timeout, call it a day on this IP and its packets
						continue
					else:
						self.net.send_packet(stalled.intf_name, stalled.arp_req) #Send ARP again
						stalled.tries += 1
					
				arp_ip[dst] = stalled #Add stalled back to the dict
				
	def router_main(self):
		arp_ip = {} #Empty dict for IP's we're waiting for ARPs on
		#Dict because it's faster than queue and we don't care about order
		
		while True:
			try:
				self.examineStalled(arp_ip) #deal with stalled that are waiting on ARPs
				
				dev,ts,pkt = self.net.recv_packet(timeout=1.0)
				payload = pkt.payload
				
				if pkt.type == pkt.ARP_TYPE: #Is an ARP
					src_ip = payload.protosrc
					dst_ip = payload.protodst
					src_eth = payload.hwsrc
					#no dst
					
					self.ip_to_ether[src_ip] = src_eth #Add to map from IP's to eth
					
					if payload.opcode == arp.REQUEST:					
						if dst_ip in self.ip_to_ether:
							hwdst = self.ip_to_ether[dst_ip]
							reply = self.makeReply(dst_ip, src_ip, hwdst, src_eth)
							self.net.send_packet(dev, reply) #send it off
						#Do nothing otherwise
					else: #ARP_REPLY
						self.ip_to_ether[src_ip] = src_eth
						#Sending dealt with in examineStalled(.) 
						
				
				elif pkt.type == pkt.IP_TYPE:
					if payload.dstip in self.my_interfaces: #Sent to us, just dropping it for now
						continue
					
					match = self.matchPrefix(payload.dstip)
					
					if match == None: #No entry on table matched
						continue #drop the packet, for now
						
					next_hop = match[1] #Ease of use
					name = match[2]
					
					if next_hop == None: #No next hop, directly connected to our port
						nxt_ip = payload.dstip
					else:
						nxt_ip = next_hop
			
					src_eth = self.nameMap[name][0] #Pull ip/eth corresponding to this interface
					src_ip = self.nameMap[name][1]

					payload.ttl -= 1
					
					ether = ethernet() #wrap ip in ether
					ether.type = ether.IP_TYPE
					ether.set_payload(payload)
					ether.src = src_eth
					
					if nxt_ip in self.ip_to_ether: #We have the mapping nxt_ip->eth
						ether.dst = self.ip_to_ether[nxt_ip]
						self.net.send_packet(name, ether) #Send packet on its way
					else:					
						if nxt_ip in arp_ip: #Already waiting on ARP for this
							arp_ip[nxt_ip].addPacket(ether)
						else: #New IP to ARP at
							request	 = self.makeRequest(nxt_ip, src_ip, src_eth) #create ARP req
							waiter = arpWaiter(name, request, ether)
							arp_ip[nxt_ip] = waiter
							
							self.net.send_packet(name, request) #Send ARP request
						
						

			except SrpyNoPackets:
				# log_debug("Timeout waiting for packets")
				continue
			except SrpyShutdown:
				return
				
class arpWaiter(object):
	'''
	Basic object to make it easier to track IP's that we're waiting on for ARPS
	
	Stores time it was made, number of ARPs sent, information necessary to send mor ARPs
	and a list of ethernet-coated packets to send off once we get an ARP reply
	'''
	def __init__(self, intf_name, arp_request, ether_pkt):
		self.start_time = time.time()
		self.tries = 1
		
		self.intf_name = intf_name
		self.arp_req = arp_request
		
		self.packet_list = [ether_pkt]
		
	def addPacket(self, ether_pkt):
		self.packet_list.append(ether_pkt)
	
	def getList(self):
		return self.packet_list

def srpy_main(net):
	'''
	Main entry point for router.  Just create Router
	object and get it going.
	'''
	r = Router(net)
	r.router_main()
	net.shutdown()
	
