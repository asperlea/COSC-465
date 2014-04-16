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




                # in the end, you should forward the packet out the same
                # device (and the packet will almost certainly have been
                # modified in some way before you send it back out.)
                self.net.send_packet(dev, pkt)

        log_info("Shutting down.")


def srpy_main(net):
    mb = Middlebox(net)
    mb.main()
    net.shutdown()
