from pox.core import core
import pox
log = core.getLogger()

from pox.lib.packet.ipv4 import ipv4,tcp
from pox.lib.addresses import IPAddr,EthAddr
import pox.openflow.libopenflow_01 as of


class p7(object):
    def __init__ (self):
        core.openflow.addListeners(self)

    def _handle_ConnectionUp(self, event):
        # yippee.  a switch connected to us.
        log.info("Got connection from {}".format(event.connection))

    def _handle_PacketIn (self, event):
        inport = event.port # input port number on which packet arrived at switch
        packet = event.parsed # reference to POX packet object
        pktin = event.ofp # reference to Openflow PacketIn message (ofp_packet_in)

        if not packet.parsed:
            log.warning("{} {} ignoring unparsed packet".format(dpid, inport))
            return

        # packet is a "normal" POX packet object
        tcphdr = packet.find('tcp')

        print packet
        print packet.payload.srcip
        if tcphdr is None:
            # for any non-TCP traffic, flood out all ports
            pktout = of.ofp_packet_out()
            action = of.ofp_action_output(port = of.OFPP_FLOOD)
            pktout.in_port = inport
            pktout.actions.append(action)
            pktout.buffer_id = event.ofp.buffer_id

            # send pktout message back to switch
            event.connection.send(pktout.pack())
        else: 
            # for any TCP traffic, install Openflow rules
            ippkt = packet.payload
            if ippkt.srcip != IPAddr("10.0.0.4") and ippkt.dstip != IPAddr("10.0.0.4"): # not from suspicious host
                outport = int(str(ippkt.dstip)[-1])
                actions = [of.ofp_action_output(port = outport)]
                flowmod = of.ofp_flow_mod(command=of.OFPFC_ADD, idle_timeout=10, hard_timeout=10, buffer_id=event.ofp.buffer_id, match = of.ofp_match.from_packet(packet, inport), actions=actions)
                event.connection.send(flowmod.pack())
            else:
                if inport == 5: # if it's coming from the middlebox
                    outport = int(str(ippkt.dstip)[-1])
                    actions = [of.ofp_action_output(port = outport)]
                    flowmod = of.ofp_flow_mod(command=of.OFPFC_ADD, idle_timeout=10, hard_timeout=10, buffer_id=event.ofp.buffer_id, match = of.ofp_match.from_packet(packet, inport), actions=actions)
                    event.connection.send(flowmod.pack())
                else:
                    outport = 5 # otherwise send it to the middlebox for proofing against the NSA and pandas
                    action1 = of.ofp_action_output(port = outport)
                    action2 = of.ofp_action_dl_addr.set_dst(EthAddr("00:00:00:00:00:05"))
                    actions = [action1]
                    actions.append(action2)
                    
                    flowmod = of.ofp_flow_mod(command=of.OFPFC_ADD, idle_timeout=10, hard_timeout=10, buffer_id=event.ofp.buffer_id, match = of.ofp_match.from_packet(packet, inport), actions=actions)
                    event.connection.send(flowmod.pack())
                

def launch():
    core.registerNew(p7)
