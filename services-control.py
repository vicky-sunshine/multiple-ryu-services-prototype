import json
from webob import Response
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
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



class ServiceControlController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(ServiceControlController, self).__init__(req,
                                                       link, data, **config)
        self.service_control_spp = data[service_control_instance_name]

    @route('service-control', urls.get_sc_sequence, methods=['GET'])
    def get_sc_sequence(self, req, **kwargs):
        dic = service_settings.service_sequence
        body = json.dumps(dic)
        return Response(status=200, content_type='application/json', body=body)

    @route('service-control', urls.get_sc_priority, methods=['GET'])
    def get_sc_priority(self, req, **kwargs):
        dic = service_settings.service_priority
        body = json.dumps(dic)
        return Response(status=200, content_type='application/json', body=body)

    @route('service-control', urls.get_sc_status, methods=['GET'])
    def get_sc_status(self, req, **kwargs):
        dic = service_settings.service_status
        body = json.dumps(dic)
        return Response(status=200, content_type='application/json', body=body)
