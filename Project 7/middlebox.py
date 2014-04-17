#!/usr/bin/env python

'''
Middlebox traffic manipulator and logger for Project 7.
'''

import sys
import os
import os.path
sys.path.append(os.path.join(os.environ['HOME'],'pox'))
sys.path.append(os.path.join(os.getcwd(),'pox'))
import pox.lib.packet as pktlib
from pox.lib.packet import ethernet,ETHER_BROADCAST,IP_ANY
from pox.lib.packet import ipv4,tcp
from pox.lib.addresses import EthAddr,IPAddr
from srpy_common import log_info, log_debug, log_warn, SrpyShutdown, SrpyNoPackets, debugger
import time

class Middlebox(object):
    def __init__(self, net):
        self.net = net

    def main(self):
        log = open("contentlog.txt", "w")
        acc_log = {}
        while True:
            try:
                dev,ts,pkt = self.net.recv_packet(timeout=1.0)
            except SrpyNoPackets:
                continue
            except SrpyShutdown:
                return

            # only deal with tcp packets; ignore everything else
            tcphdr = pkt.find('tcp')
            if tcphdr is not None:
                log_debug("Got packet for TCP source: {}".format(pkt.dump()))

                # your code should start at this indentation level; you're
                # only concerned with TCP packets.  
                
                ippkt = pkt.payload
                tcppkt = ippkt.payload
                message = tcppkt.payload

                # adding message to log
                log_key = str(ippkt.srcip) + ":" + str(tcppkt.srcport) + ":" + str(ippkt.dstip) + ":" + str(tcppkt.dstport)
                acc_log[log_key] = (time.asctime(), message)

                if "NSA" in message:
                    index = message.find("NSA")
                    message = message[0:index] + "Fluffy Bunnies" + message[index + 3:]
                
                if "panda" in message:
                    tcppkt.RST = 1
                    message = ""
                
                # re-wrap packet
                tcppkt.set_payload(message)
                tcppkt.tcplen = 20 + len(message)
                ippkt.set_payload(tcppkt)
                pkt.set_payload(ippkt)
                dest = str(ippkt.dstip)[-1]
                pkt.dst = EthAddr("00:00:00:00:00:0" + dest)
                    
                if tcppkt.RST or tcppkt.FIN: # write log to file
                    for entry in acc_log:
                        log.write(acc_log[entry][0] + "  " + entry + "  " + acc_log[entry][1])
                    log.close()                

                # in the end, you should forward the packet out the same
                # device (and the packet will almost certainly have been                # modified in some way before you send it back out.)
                self.net.send_packet(dev, pkt)

        log_info("Shutting down.")
        for entry in acc_log:
            log.write(acc_log[entry][0] + "  " + entry + "  " + acc_log[entry][1])
        log.close() 


def srpy_main(net):
    mb = Middlebox(net)
    mb.main()
    net.shutdown()
