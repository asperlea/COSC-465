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
        
    def makeEcho(self, request):
        icmppkt = pktlib.icmp()
        icmppkt.type = pktlib.TYPE_ECHO_REPLY

        reply = pktlib.echo()
        reply.id = request.id
        reply.seq = request.seq
        reply.payload = request.payload

        icmppkt.payload = reply
        return icmppkt

    def makeICMP(self, errorType, codeType, ippkt):
        icmppkt = pktlib.icmp()
        icmppkt.type = errorType
        icmppkt.code = codeType
        icmppkt.payload = pktlib.unreach()
        
        icmppkt.payload.payload = ippkt.dump()[:28]
        return icmppkt

    def makeIP(self, icmppkt, ipsrc, ipdest):
        ippkt = pktlib.ipv4()
        ippkt.srcip = ipdest
        ippkt.dstip = ipsrc
        ippkt.ttl = 64 # a reasonable initial TTL value
        ippkt.protocol = ippkt.ICMP_PROTOCOL
        ippkt.payload = icmppkt
        return ippkt
        
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
        forTable = open("forwarding_table3.txt", "r")
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
        
    def forward_packet(self, pkt, dev):
        payload = pkt.payload
        
        match = self.matchPrefix(payload.dstip)
        if match == None: #No entry on table matched
            icmp_error = self.makeICMP(pktlib.TYPE_DEST_UNREACH, pktlib.CODE_UNREACH_NET, payload) # make ICMP error
            ip_reply = self.makeIP(icmp_error, payload.srcip, self.nameMap[dev][1]) # wrap it in IP
            pkt.payload = ip_reply # send it off
            payload = pkt.payload
            match = self.matchPrefix(payload.dstip)
        
        next_hop = match[1] #Ease of use
        name = match[2]
        
        if next_hop == None: #No next hop, directly connected to our port
            nxt_ip = payload.dstip
        else:
            nxt_ip = next_hop

        src_eth = self.nameMap[name][0] #Pull ip/eth corresponding to this interface
        src_ip = self.nameMap[name][1]
        
        ether = ethernet() #wrap ip in ether
        ether.type = ether.IP_TYPE
        ether.set_payload(payload)
        ether.src = src_eth
        if nxt_ip in self.ip_to_ether: #We have the mapping nxt_ip->eth
            ether.dst = self.ip_to_ether[nxt_ip]
            self.net.send_packet(name, ether) #Send packet on its way
        else:                    
            if nxt_ip in self.arp_ip: #Already waiting on ARP for this
                self.arp_ip[nxt_ip].addPacket(ether)
            else: #New IP to ARP at
                request = self.makeRequest(nxt_ip, src_ip, src_eth) #create ARP req
                waiter = arpWaiter(name, request, ether, dev)
                self.arp_ip[nxt_ip] = waiter
                self.net.send_packet(name, request) #Send ARP request


    def examineStalled(self):
        keys = self.arp_ip.keys() #Can/will lose keys during iteration
        for dst in keys:
            stalled = self.arp_ip.pop(dst)
            
            if dst in self.ip_to_ether: #We've since figured this one out
                dst_eth = self.ip_to_ether[dst]
                
                for ether_pkt in stalled.getList(): #Send out all the waiting packets
                    ether_pkt.dst = dst_eth
                    self.net.send_packet(stalled.intf_name, ether_pkt)
            else:
                difference = time.time() - stalled.start_time
            
                sentICMP = False
                if difference/stalled.tries > 1:
                    if stalled.tries >=5: #Timeout, send ICMP timeout
                        ether = stalled.packet_list[0] # one of the ethernet packets that are queued up is all we need to get IP info
                        icmp_error = self.makeICMP(pktlib.TYPE_DEST_UNREACH, pktlib.CODE_UNREACH_HOST, ether.payload)
                        ip_reply = self.makeIP(icmp_error, ether.payload.srcip, self.nameMap[stalled.dev][1])
                        ether = ethernet() #wrap ip in ether because forward_packet uses ethernet packets
                        ether.type = ether.IP_TYPE
                        ether.set_payload(ip_reply)
                        self.forward_packet(ether, stalled.intf_name) 
                        sentICMP = True
                    else:
                        self.net.send_packet(stalled.intf_name, stalled.arp_req) #Send ARP again
                        stalled.tries += 1
                    
                if not sentICMP:
                    self.arp_ip[dst] = stalled #Add stalled back to the dict
                
    def router_main(self):
        self.arp_ip = {} #Empty dict for IP's we're waiting for ARPs on
        #Dict because it's faster than queue and we don't care about order
        
        while True:
            try:
                self.examineStalled() #deal with stalled that are waiting on ARPs
                
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
                    if payload.dstip in self.my_interfaces: #Sent to us
                        inner = payload.payload
                        if inner.find("icmp") and inner.type == pktlib.TYPE_ECHO_REQUEST:
                            icmp_reply = self.makeEcho(inner.payload) # make ICMP header
                            ip_reply = self.makeIP(icmp_reply, payload.srcip, self.nameMap[dev][1]) # make IP header
                            pkt.payload = ip_reply # put it in the packet to be sent forward
                            payload = pkt.payload
                        else:
                            icmp_error = self.makeICMP(pktlib.TYPE_DEST_UNREACH, pktlib.CODE_UNREACH_PORT, payload) # make ICMP error
                            ip_reply = self.makeIP(icmp_error, payload.srcip, self.nameMap[dev][1]) # make IP header
                            pkt.payload = ip_reply # put it in the packet to be sent forward
                            payload = pkt.payload

                    payload.ttl -= 1
                    if payload.ttl == 0:
                        icmp_error = self.makeICMP(pktlib.TYPE_TIME_EXCEED, 0, payload) # make ICMP error
                        ip_reply = self.makeIP(icmp_error, payload.srcip, self.nameMap[dev][1]) # wrap it in IP
                        pkt.payload = ip_reply # send it off
                        payload = pkt.payload
                    self.forward_packet(pkt, dev)

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
    def __init__(self, intf_name, arp_request, ether_pkt, dev):
        self.start_time = time.time()
        self.tries = 1
        self.dev = dev
        
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
    
