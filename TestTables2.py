from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ether
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet import icmp
from ryu.lib.packet import tcp
from ryu.lib.packet import udp


class SimpleSwitch13(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	def __init__(self, *args, **kwargs):
		super(SimpleSwitch13, self).__init__(*args, **kwargs)
		self.mac_to_port = {}
		self.add_a_flow = 0
		self.flows_eth = []
		self.table1 = ["10.0.0.1", "10.0.0.2"]
		self.table2 = ["10.0.0.3", "10.0.0.4"]

	@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
	def switch_features_handler(self, ev):
		datapath = ev.msg.datapath
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		# install table-miss flow entry
		#
		# We specify NO BUFFER to max_len of the output action due to
		# OVS bug. At this moment, if we specify a lesser number, e.g.,
		# 128, OVS will send Packet-In with invalid buffer_id and
		# truncated packet data. In that case, we cannot output packets
		# correctly.
		match = parser.OFPMatch()
		actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
		                                  ofproto.OFPCML_NO_BUFFER)]
		inst = [datapath.ofproto_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
		#self.add_flow(datapath, 0, match, inst)
		self.add_flow(datapath, 0, 0, match, inst)
		self.add_flow(datapath, 1, 0, match, inst)
		self.add_flow(datapath, 2, 0, match, inst)


	def add_flow(self, datapath, table_id, priority, match, inst):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		
		mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id, priority=priority, match=match, instructions=inst)
		datapath.send_msg(mod)	

	def parse_msg(self, protocol, msg):
		msg = str(msg)
		if protocol in ["eth", "ipv4"]:
			src = msg.split("src='")[1].split("'")[0]
			dst = msg.split("dst='")[1].split("'")[0]
			return [src, dst]
		elif protocol in ["arp"]:
			opcode = msg.split("opcode=")[1].split(",plen")[0]
			src_eth = msg.split("src_mac='")[1].split("')]")[0]
			dst_eth = msg.split("dst_mac='")[1].split("',hlen")[0]
			src_ip = msg.split("src_ip='")[1].split("',src_mac")[0]
			dst_ip = msg.split("dst_ip='")[1].split("',dst_mac")[0]
			return [opcode, src_eth, dst_eth, src_ip, dst_ip]


	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		msg = ev.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		in_port = msg.match['in_port']
		#table_id = msg.match['table_id']
		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocols(ethernet.ethernet)[0]
		arp_in = pkt.get_protocols(arp.arp)
		ip = pkt.get_protocols(ipv4.ipv4)

		src_eth = eth.src
		dst_eth = eth.dst

		dpid = datapath.id
		self.mac_to_port.setdefault(dpid, {})

		#self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

		# learn a mac address to avoid FLOOD next time.
		self.mac_to_port[dpid][src_eth] = in_port

		if dst_eth in self.mac_to_port[dpid]:
			out_port = self.mac_to_port[dpid][dst_eth]
		else:
			out_port = ofproto.OFPP_FLOOD

		actions = [parser.OFPActionOutput(out_port)]

		# install a flow to avoid packet_in next time
		print("1")
		self.add_a_flow = 0
		if out_port != ofproto.OFPP_FLOOD:
			print("2")
			if arp_in:
				print(arp_in)
			if ip:
				eth_pair = src_eth + " to " + dst_eth
				[src_ip, dst_ip] = self.parse_msg("ipv4", ip)
				if eth_pair in self.flows_eth:
					print("eth flow exists, add IP flow")
					match = datapath.ofproto_parser.OFPMatch(eth_type=ether.ETH_TYPE_IP, in_port=in_port, ipv4_src=src_ip, ipv4_dst=dst_ip)
					inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
					which_table = -1
					if src_ip in self.table1:
						which_table = 1
					elif src_ip in self.table2:
						which_table = 2
					self.add_flow(datapath, which_table, 1, match, inst)
					self.add_a_flow = 1
					print("%s to %s added (table %d)" % (src_ip, dst_ip, which_table))
				else:
					print("eth flow doesn't exist, add eth flow")
					self.flows_eth.append("%s to %s" % (src_eth, dst_eth))
					which_table = -1
					if src_ip in self.table1:
						which_table = 1
					elif src_ip in self.table2:
						which_table = 2
					match = datapath.ofproto_parser.OFPMatch(in_port=in_port, eth_src=src_eth, eth_dst=dst_eth)
					inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, []), parser.OFPInstructionGotoTable(which_table)]
					self.add_flow(datapath, 0, 1, match, inst)
					print("%s to %s added" % (src_eth, dst_eth))

			else:
				#match = datapath.ofproto_parser.OFPMatch(eth_type=ether.ETH_TYPE_ARP, in_port=in_port, eth_src=src_eth, eth_dst=dst_eth)
				match = datapath.ofproto_parser.OFPMatch(in_port=in_port, eth_src=src_eth, eth_dst=dst_eth)
				[opcode, src_eth, dst_eth, src_ip, dst_ip] = self.parse_msg("arp", arp_in)
				which_table = -1
				if src_ip in self.table1:
					which_table = 1
				elif src_ip in self.table2:
					which_table = 2
				else:
					print("source ip is not in table1 or table2")
					return
				inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, []), parser.OFPInstructionGotoTable(which_table)]
				self.add_flow(datapath, 0, 1, match, inst)
				self.flows_eth.append("%s to %s" % (src_eth, dst_eth))
				print("add %s at table %d " % (self.flows_eth[-1], which_table))
		else:
			if arp_in:
				print("got an arp request from " + src_eth)


		if self.add_a_flow == 1:
			print("no pkt out, should go through flows")
		else:
			data = None
			if msg.buffer_id == ofproto.OFP_NO_BUFFER:
				data = msg.data

			out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
			datapath.send_msg(out)
			print("pkt_out")
