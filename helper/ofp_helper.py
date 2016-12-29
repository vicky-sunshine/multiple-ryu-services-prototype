def add_flow(datapath, priority, match, actions, table_id=0,
             idle_timeout=0, buffer_id=None):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    next_table = table_id + 1
    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                         actions),
            parser.OFPInstructionGotoTable(next_table)]
    if buffer_id:
        mod = parser.OFPFlowMod(datapath=datapath,
                                idle_timeout=idle_timeout,
                                buffer_id=buffer_id,
                                priority=priority,
                                match=match,
                                table_id=table_id,
                                instructions=inst)
    else:
        mod = parser.OFPFlowMod(datapath=datapath,
                                idle_timeout=idle_timeout,
                                priority=priority,
                                match=match,
                                table_id=table_id,
                                instructions=inst)
    datapath.send_msg(mod)


def del_flow(datapath, match, priority, table_id):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    mod = parser.OFPFlowMod(datapath=datapath,
                            command=ofproto.OFPFC_DELETE_STRICT,
                            out_port=ofproto.OFPP_ANY,
                            out_group=ofproto.OFPG_ANY,
                            priority=priority,
                            match=match,
                            table_id=table_id)
    datapath.send_msg(mod)


def send_packet(datapath, pkt, port):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    pkt.serialize()

    data = pkt.data
    actions = [parser.OFPActionOutput(port=port)]
    out = parser.OFPPacketOut(datapath=datapath,
                              buffer_id=ofproto.OFP_NO_BUFFER,
                              in_port=ofproto.OFPP_CONTROLLER,
                              actions=actions,
                              data=data)
    datapath.send_msg(out)
