import http
import json
import logging
import threading

from oslo_config import cfg
import oslo_messaging

from simple_websocket_server import WebSocketServer, WebSocket


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger()



class NotificationForwarder(object):

    def forward(self):
        self.start_http()
        self.endpoint = NotificationEndpoint()
        self.start_websocket()
        self.listen_to_notifications()

    def start_http(self):
        LOG.info('httpd starting')
        server_address = ('', 8080)
        httpd = http.server.HTTPServer(
            server_address, http.server.SimpleHTTPRequestHandler)
        threading.Thread(target=httpd.serve_forever).start()
        LOG.info('httpd started')
    
    def on_connect(self, *args, **kwargs):
        LOG.info('ws client connected %s, %s', args, kwargs)
        ws = WsServer(*args, **kwargs)
        self.endpoint.client = ws
        return ws

    def start_websocket(self):
        LOG.info('ws starting')
        server = WebSocketServer('', 8000, self.on_connect)
        threading.Thread(target=server.serve_forever).start()
        LOG.info('ws started')

    def listen_to_notifications(self):
        cfg.CONF()

        transport = oslo_messaging.get_notification_transport(
            cfg.CONF, url='rabbit://stackrabbit:admin@127.0.0.1:5672/')

        targets = [
            oslo_messaging.Target(topic='versioned_notifications'),
        ]

        endpoints = [self.endpoint]

        server = oslo_messaging.get_notification_listener(
                transport, targets, endpoints, executor='threading')

        LOG.info("messaging starting")
        server.start()
        LOG.info("messaging started")
        server.wait()
        LOG.info("exit")


class WsServer(WebSocket):

    def handle(self):
        pass

    def connected(self):
        pass

    def handle_close(self):
        LOG.info('ws client disconnected')


class NotificationEndpoint(object):

    def __init__(self):
        self.client = None

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        LOG.info('notification received %s:%s' % 
                 (publisher_id, event_type))
        if self.client:
            LOG.info('forwarding to ' + str(self.client.address))
            #self.client.send_message(
            #    json.dumps({
            #        "payload": payload,
            #        "publisher_id": publisher_id,
            #        "event_type": event_type}))
            if event_type.startswith("instance."):
                self.client.send_message("%s:%s" % (payload["nova_object.data"]["uuid"], event_type))




if __name__ == '__main__':
    NotificationForwarder().forward()
