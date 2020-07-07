import socket
import ssl
import json
import struct
import random
import sys
import time
import logging
import threading
import os
import logging


class HassProxyApp:
    def __init__(self):
        self.reconnect_interval = 5
        self.ping_interval = 1
        self.pingtime = 0
        self.ClientId = ''
        self.mainsocket = None
        self.stop_flag = False

        self.client_hostname = ''

    def run_reverse_proxy(self, hass, cfg):
        logger = logging.getLogger('%s' % 'hassproxy client')
        logger.info('Starting reverse proxy')
        self.hass_context = hass
        self.server_host = cfg.get('server_host')
        self.server_port = cfg.get('server_port')
        self.client_bufsize = cfg.get('client_bufsize')
        self.client_subdomain = cfg.get('client_openid')
        self.client_protocol = cfg.get('client_protocol')
        self.client_lport = cfg.get('client_lport')
        self.client_rport = cfg.get('client_rport')
        self.client_lhost = cfg.get('client_lhost')
        self.stop_flag = False

        self.ping_thread = threading.Thread(target=self.ping_server)
        self.ping_thread.setDaemon(True)
        self.ping_thread.start()

        self.main_thread = threading.Thread(target=self.proxy_loop)
        self.main_thread.setDaemon(True)
        self.main_thread.start()

    def stop_reverse_proxy(self):
        logger = logging.getLogger('%s' % 'hassproxy client')
        logger.info('Stopping reverse proxy...')
        self.stop_flag = True
        if self.mainsocket:
            try:
                self.mainsocket.shutdown(socket.SHUT_WR)
            except socket.error:
                self.mainsocket.close()
            finally:
                self.mainsocket = None

    def proxy_loop(self):
        while not self.stop_flag:
            try:
                # 检测控制连接是否连接.
                if not self.mainsocket:
                    ip = self.dnsopen(self.server_host)
                    if not ip:
                        logger = logging.getLogger('%s' % 'hassproxy client')
                        logger.info('update dns')
                        time.sleep(self.reconnect_interval)
                        continue
                    self.mainsocket = self.connectremote(ip, self.server_port)
                    if not self.mainsocket:
                        logger = logging.getLogger('%s' % 'hassproxy client')
                        logger.info('connect failed...!')
                        time.sleep(self.reconnect_interval)
                        continue
                    thread = threading.Thread(target=self.HKClient,
                                              args=(self.mainsocket, 0, 1))
                    thread.setDaemon(True)
                    thread.start()
                time.sleep(self.ping_interval)
            except socket.error:
                self.pingtime = 0
                time.sleep(self.reconnect_interval * 2)
                logger = logging.getLogger('%s' % 'hassproxy client')
                logger.info('Hassproxy reconnect failed, retry......')

    def ping_server(self):
        while not self.stop_flag:
            try:
                # 发送心跳
                if self.pingtime + 20 < time.time(
                ) and self.pingtime != 0 and self.mainsocket:
                    self.sendpack(self.mainsocket, self.Ping())
                    self.pingtime = time.time()
                time.sleep(self.ping_interval)
            except socket.error:
                self.pingtime = 0
                time.sleep(self.reconnect_interval * 2)
                logger = logging.getLogger('%s' % 'hassproxy client')
                logger.debug('Hassproxy reconnecting...')

    def dnsopen(self, host):
        try:
            ip = socket.gethostbyname(host)
            return ip
        except socket.error:
            return None

    def connectremote(self, host, port):
        try:
            host = socket.gethostbyname(host)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ssl_client = ssl.wrap_socket(client,
                                         ssl_version=ssl.PROTOCOL_SSLv23)
            ssl_client.connect((host, port))
            ssl_client.setblocking(1)
            logger = logging.getLogger('%s:%d' % ('Conn', ssl_client.fileno()))
            logger.debug('New connection to: %s:%d' % (host, port))
        except socket.error:
            return False
        return ssl_client

    def connectlocal(self, localhost, localport):
        try:
            localhost = socket.gethostbyname(localhost)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((localhost, localport))
            client.setblocking(1)
            logger = logging.getLogger('%s:%d' % ('Conn', client.fileno()))
            logger.debug('New connection to: %s:%d' % (localhost, localport))
        except socket.error:
            return False
        return client

    def NgrokAuth(self):
        Payload = dict()
        Payload['ClientId'] = ''
        Payload['OS'] = 'darwin'
        Payload['Arch'] = 'amd64'
        Payload['Version'] = '2'
        Payload['MmVersion'] = '1.7'
        Payload['User'] = 'user'
        Payload['Password'] = ''
        body = dict()
        body['Type'] = 'Auth'
        body['Payload'] = Payload
        buffer = json.dumps(body)
        return (buffer)

    def ReqTunnel(self, ReqId, Protocol, Hostname, Subdomain, RemotePort):
        Payload = dict()
        Payload['ReqId'] = ReqId
        Payload['Protocol'] = Protocol
        Payload['Hostname'] = Hostname
        Payload['Subdomain'] = Subdomain
        Payload['HttpAuth'] = ''
        Payload['RemotePort'] = RemotePort
        body = dict()
        body['Type'] = 'ReqTunnel'
        body['Payload'] = Payload
        buffer = json.dumps(body)
        return (buffer)

    def RegProxy(self, ClientId):
        Payload = dict()
        Payload['ClientId'] = ClientId
        body = dict()
        body['Type'] = 'RegProxy'
        body['Payload'] = Payload
        buffer = json.dumps(body)
        return (buffer)

    def Ping(self):
        Payload = dict()
        body = dict()
        body['Type'] = 'Ping'
        body['Payload'] = Payload
        buffer = json.dumps(body)
        return (buffer)

    def lentobyte(self, len):
        return struct.pack('<LL', len, 0)

    def sendbuf(self, sock, buf, isblock=False):
        if isblock:
            sock.setblocking(1)
        sock.sendall(buf)
        if isblock:
            sock.setblocking(0)

    def sendpack(self, sock, msg, isblock=False):
        if isblock:
            sock.setblocking(1)
        sock.sendall(self.lentobyte(len(msg)) + msg.encode('utf-8'))
        logger = logging.getLogger('%s:%d' % ('Send', sock.fileno()))
        logger.debug('Writing message: %s' % msg)
        if isblock:
            sock.setblocking(0)

    def tolen(self, v):
        if len(v) == 8:
            return struct.unpack('<II', v)[0]
        return 0

    def getRandChar(self, length):
        _chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz"
        return ''.join(random.sample(_chars, length))

    # 客户端程序处理过程
    def HKClient(self, sock, linkstate, type, tosock=None):
        recvbuf = bytes()
        while not self.stop_flag:
            try:
                if linkstate == 0:
                    if type == 1:
                        self.sendpack(sock, self.NgrokAuth(), False)
                        linkstate = 1
                    if type == 2:
                        self.sendpack(sock, self.RegProxy(self.ClientId),
                                      False)
                        linkstate = 1
                    if type == 3:
                        linkstate = 1

                recvbut = sock.recv(self.client_bufsize)
                if not recvbut: break

                if len(recvbut) > 0:
                    if not recvbuf:
                        recvbuf = recvbut
                    else:
                        recvbuf += recvbut

                if type == 1 or (type == 2 and linkstate == 1):
                    lenbyte = self.tolen(recvbuf[0:8])
                    if len(recvbuf) >= (8 + lenbyte):
                        buf = recvbuf[8:lenbyte + 8].decode('utf-8')
                        js = json.loads(buf)
                        if type == 1:
                            if js['Type'] == 'ReqProxy':
                                newsock = self.connectremote(
                                    self.server_host, self.server_port)
                                if newsock:
                                    thread = threading.Thread(
                                        target=self.HKClient,
                                        args=(newsock, 0, 2))
                                    thread.setDaemon(True)
                                    thread.start()
                            if js['Type'] == 'AuthResp':
                                self.ClientId = js['Payload']['ClientId']
                                logger = logging.getLogger('%s' %
                                                           'hassproxy client')
                                logger.info(
                                    'Authenticated with server, client id: %s'
                                    % self.ClientId)
                                self.sendpack(sock, self.Ping())
                                self.pingtime = time.time()
                                reqid = self.getRandChar(8)
                                self.sendpack(
                                    sock,
                                    self.ReqTunnel(reqid, self.client_protocol,
                                                   self.client_hostname,
                                                   self.client_subdomain,
                                                   self.client_rport))
                            if js['Type'] == 'NewTunnel':
                                if js['Payload']['Error'] != '':
                                    logger = logging.getLogger(
                                        '%s' % 'hassproxy client')
                                    logger.error(
                                        'Server failed to allocate tunnel: %s'
                                        % js['Payload']['Error'])
                                    time.sleep(30)
                                else:
                                    logger = logging.getLogger(
                                        '%s' % 'hassproxy client')
                                    logger.info('Tunnel established at %s' %
                                                js['Payload']['Url'])
                        if type == 2:
                            if js['Type'] == 'StartProxy':
                                newsock = self.connectlocal(
                                    self.client_lhost, self.client_lport)
                                if newsock:
                                    thread = threading.Thread(
                                        target=self.HKClient,
                                        args=(newsock, 0, 3, sock))
                                    thread.setDaemon(True)
                                    thread.start()
                                    tosock = newsock
                                    linkstate = 2
                                else:
                                    body = '<html><body style="background-color: #97a8b9"><div style="margin:auto; width:400px;padding: 20px 60px; background-color: #D3D3D3; border: 5px solid maroon;"><h2>Tunnel %s unavailable</h2><p>Unable to initiate connection to <strong>%s</strong>. This port is not yet available for web server.</p>'
                                    html = body % (js['Payload']['Url'],
                                                   self.client_lhost + ':' +
                                                   str(self.client_lport))
                                    header = "HTTP/1.0 502 Bad Gateway" + "\r\n"
                                    header += "Content-Type: text/html" + "\r\n"
                                    header += "Content-Length: %d" + "\r\n"
                                    header += "\r\n" + "%s"
                                    buf = header % (len(
                                        html.encode('utf-8')), html)
                                    self.sendbuf(sock, buf.encode('utf-8'))

                        if len(recvbuf) == (8 + lenbyte):
                            recvbuf = bytes()
                        else:
                            recvbuf = recvbuf[8 + lenbyte:]

                if type == 3 or (type == 2 and linkstate == 2):
                    self.sendbuf(tosock, recvbuf)
                    recvbuf = bytes()

            except socket.error:
                break

        if type == 1:
            self.mainsocket = None
        if type == 3:
            try:
                tosock.shutdown(socket.SHUT_WR)
            except socket.error:
                tosock.close()

        logger = logging.getLogger('%s:%d' % ('Close', sock.fileno()))
        logger.debug('Closing')
        sock.close()


HASS_PROXY_APP = HassProxyApp()