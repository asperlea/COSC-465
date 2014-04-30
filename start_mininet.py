#!/usr/bin/python

import sys
import argparse
import os
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg
from mininet.link import TCLink

parser = argparse.ArgumentParser(description="Mininet testbed for project 8")
args = parser.parse_args()
lg.setLogLevel('info')

class MyTopo(Topo):
    def __init__(self, args):
        super(MyTopo, self).__init__()

        self.addHost('h1')
        self.addHost('h2')
        self.addSwitch('s1')
        self.addSwitch('s2')
        self.addLink('h1', 's1')
        self.addLink('h2', 's2')
        self.addLink('s1', 's2', bw=10, delay='25ms')
        
def main():
    topo = MyTopo(args)
    net = Mininet(topo=topo, link=TCLink, cleanup=True)
    net.interact()

if __name__ == '__main__':
    main()
