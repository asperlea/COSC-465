#!/usr/bin/env python

'''
Basic IPv4 router (static routing) in Python, stage 1.
Authors: Curtis Mahoney * Adriana Sperlea
Date: 2/20/2014
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
from pox.lib.addresses import EthAddr,IPAddr
from srpy_common import log_info, log_debug, log_warn, SrpyShutdown, SrpyNoPackets, debugger

class Router(object):
    def __init__(self, net):
	self.net = net
	self.ip_to_ether = {} #Empty dict to store mappings
	self.my_interfaces = {}
		
	for intf in net.interfaces():
	    self.my_interfaces[intf.ipaddr] = intf.ethaddr
			
    def findEth(self, ip, ipToEther):
	'''
        Returns the Ethernet address for an IP address given a dictionary of IP to ethernet
        '''
        if ip in ipToEther:
            return ipToEther[ip]
        return None

    def addToEth(self, ip, eth, ipToEther):
        '''
        Adds an IP to Ethernet address to a dictionary of IP to ethernet
        '''
        if not (ip in ipToEther):
            ipToEther[ip] = eth

    def makeReply(self, dst_ip, src_ip, hwdst, src_eth):
        '''
        Creates an ARP reply packet given IP source and destination, Ethernet source and destination
        '''

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

        return ether
        
    def createForwardingTable(self):
        '''
        Creates a Forwarding Table for the router.
        All addresses in forwarding table are stored in binary for easy bitwise operations
        '''
        self.forwardingTable = {}
        
        #Obtain routes from net.interfaces
        for intf in self.net.interfaces():
            prefix = intf.ipaddr.toUnsigned() & intf.netmask.toUnsigned() # network prefix
            mask = intf.netmask.toUnsigned() # network mask
            nexthop = intf.ipaddr # next hop
            name = intf.name # interface name

            self.forwardingTable[prefix] = tuple([mask, nexthop, name])

        #Obtain routes from forwarding_table.txt
        forTable = open("forwarding_table.txt", "r")
        for line in forTable:
            parsedLine = line.split(" ")
            prefix = parsedLine[0].toUnsigned() # network prefix
            mask = parsedLine[1].toUnsigned() # network mask
            nexthop = parsedLine[2] # next hop
            name = parsedLine[3] # interface name

            self.forwardingTable[prefix] = tuple([mask, nexthop, name]]))

    def router_main(self):
        self.createForwardingTable()

	while True:
	    try:
		dev,ts,pkt = self.net.recv_packet(timeout=1.0)
		payload = pkt.payload
				
		if pkt.find("arp"): #Is an ARP
	            src_ip = payload.protosrc
        	    dst_ip = payload.protodst
		    src_eth = payload.hwsrc
		    #no dst
					
                    self.addToEth(src_ip, src_eth, self.ip_to_ether) #For later use\
					
                    hwdst = self.findEth(dst_ip) #look up eth
							
		    if hwdst != None: #if we have that ip
                        reply = self.makeReply(dst_ip, src_ip, hwdst, src_eth)
                        
                        self.net.send_packet(dev, reply) #send it off
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
	
