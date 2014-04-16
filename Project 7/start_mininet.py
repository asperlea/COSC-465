#!/usr/bin/python

import sys

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg
from mininet.node import CPULimitedHost,RemoteController,OVSSwitch
from mininet.link import TCLink
from mininet.util import irange, custom, quietRun, dumpNetConnections
from mininet.cli import CLI

from time import sleep, time
from subprocess import Popen, PIPE
import subprocess
import argparse
import os

parser = argparse.ArgumentParser(description="Mininet setup for sdn project")
# no arguments needed as yet :-)
args = parser.parse_args()
lg.setLogLevel('info')

class PyRouterTopo(Topo):

    def __init__(self, args):
        # Add default members to class.
        super(PyRouterTopo, self).__init__()

        # Host and link configuration
        #
        # h2-\  mb
        #     \ |
        # h3----s1---h1
        #     /
        # h4-/

        self.addSwitch('s1')
        self.addHost('mb')
        for i in xrange(1,5):
            self.addHost('h{}'.format(i))
            self.addLink('h{}'.format(i),'s1',bw=1000,delay='5ms')
        self.addLink('s1','mb',bw=1000)

        # hx ip address: 10.0.0.x
        # hx: mac address: 00:00:00:00:00:0x
        # mb: mac address: 00:00:00:00:00:05

def start_webservers(net):
    for i in xrange(2,5):
        host = net.get('h{}'.format(i))
        if not host.waiting:
            host.sendCmd('./www/start_webserver.sh')

def main():
    topo = PyRouterTopo(args)
    net = Mininet(topo=topo, link=TCLink, autoSetMacs=True, cleanup=True, listenPort=10001, controller=RemoteController)
    mb = net.get('mb')
    mb.setIP('0.0.0.0') # don't set an IP address on middlebox
    net.staticArp()
    start_webservers(net)
    net.interact()

if __name__ == '__main__':
    main()
