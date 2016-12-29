from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

from route import urls
from helper import ofp_helper
from config import service_sequence, service_priority

class App1(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(App1, self).__init__(*args, **kwargs)
        self.apply_table_id = service_sequence.app1
        self.service_priority = service_priority.app1

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionSetField(eth_src='AA:BB:CC:DD:EE:FF')]
        ofp_helper.add_flow(datapath, self.apply_table_id, self.service_priority, match, actions)
