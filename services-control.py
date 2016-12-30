import json
from webob import Response
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.topology.api import get_switch
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

from route import urls
from helper import ofp_helper
from config import service_settings

service_control_instance_name = 'service_control_api_app'

class ServiceControl(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(ServiceControl, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(ServiceControlController,
                      {service_control_instance_name: self})
        self.topology_api_app = self
        self.service_priority = service_settings.service_priority['service_control']

    def add_passby_flow(self, apply_table_id):
        switch_list = get_switch(self.topology_api_app, None)
        for switch in switch_list:
            datapath = switch.dp
            parser = datapath.ofproto_parser
            match = parser.OFPMatch()
            next_table = apply_table_id + 1
            instructions = [parser.OFPInstructionGotoTable(next_table)]
            ofp_helper.add_flow(datapath, apply_table_id, self.service_priority, match, instructions)

    def delete_passby_flow(self, apply_table_id):
        switch_list = get_switch(self.topology_api_app, None)
        for switch in switch_list:
            datapath = switch.dp
            parser = datapath.ofproto_parser
            match = parser.OFPMatch()
            ofp_helper.del_flow(datapath, apply_table_id, self.service_priority, match)

    def enable_service(self, service_name):
        apply_table_id = service_settings.service_sequence[service_name]
        self.delete_passby_flow(apply_table_id)
        service_settings.service_status[service_name] = True

    def disable_service(self, service_name):
        apply_table_id = service_settings.service_sequence[service_name]
        self.add_passby_flow(apply_table_id)
        service_settings.service_status[service_name] = False


class ServiceControlController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(ServiceControlController, self).__init__(req,
                                                       link, data, **config)
        self.service_control_spp = data[service_control_instance_name]

    # GET '/service-control/sequence'
    @route('service-control', urls.get_sc_sequence, methods=['GET'])
    def get_sc_sequence(self, req, **kwargs):
        dic = service_settings.service_sequence
        body = json.dumps(dic)
        return Response(status=200, content_type='application/json', body=body)

    # GET '/service-control/priority'
    @route('service-control', urls.get_sc_priority, methods=['GET'])
    def get_sc_priority(self, req, **kwargs):
        dic = service_settings.service_priority
        body = json.dumps(dic)
        return Response(status=200, content_type='application/json', body=body)

    # GET '/service-control/status'
    @route('service-control', urls.get_sc_status, methods=['GET'])
    def get_sc_status(self, req, **kwargs):
        dic = service_settings.service_status
        body = json.dumps(dic)
        return Response(status=200, content_type='application/json', body=body)

    # PUT '/service-control/enable'
    @route('service-control', urls.put_service_enable, methods=['PUT'])
    def put_service_enable(self, req, **kwargs):
        service_control = self.service_control_spp
        content = req.body
        json_data = json.loads(content)
        service_name = str(json_data.get('service_name'))

        service_control.enable_service(service_name)
        return Response(status=202, content_type='application/json')

    # PUT '/service-control/disable'
    @route('service-control', urls.put_service_disable, methods=['PUT'])
    def put_service_disable(self, req, **kwargs):
        service_control = self.service_control_spp
        content = req.body
        json_data = json.loads(content)
        service_name = str(json_data.get('service_name'))

        service_control.disable_service(service_name)
        return Response(status=202, content_type='application/json')
