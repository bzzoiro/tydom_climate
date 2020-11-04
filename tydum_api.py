#!/usr/bin/env python
import asyncio
import  websockets

import os
import logging
import json
import base64

from io import BytesIO
from http.client import HTTPResponse
import urllib3

from requests.auth import HTTPDigestAuth
import requests


host = 'mediation.tydom.com'
cmd_prefix = "\x02"

ENDPOINT = None

#loop = asyncio.get_event_loop()
loop = asyncio.new_event_loop()

_LOGGER = logging.getLogger(__name__)


def build_digest_headers(nonce, payload):

    username = payload['username']
    password = payload['password']
    host = payload['host']
    
    digestAuth = HTTPDigestAuth(username, password)
    chal = dict()
    chal["nonce"] = nonce[2].split('=', 1)[1].split('"')[1]
    chal["realm"] = "ServiceMedia"
    chal["qop"] = "auth"
    digestAuth._thread_local.chal = chal
    digestAuth._thread_local.last_nonce = nonce
    digestAuth._thread_local.nonce_count = 1
    
    a = digestAuth.build_digest_header('GET', "https://{}:443/mediation/client?mac={}&appli=1".format(host, username))
    return a

def generate_random_key():
    return base64.b64encode(os.urandom(16))

class BytesIOSocket:
    def __init__(self, content):
        self.handle = BytesIO(content)

    def makefile(self, mode):
        return self.handle

def response_from_bytes(data):
    sock = BytesIOSocket(data)
    response = HTTPResponse(sock)
    response.begin()
    return urllib3.HTTPResponse.from_httplib(response).data.decode("utf-8")

def put_response_from_bytes(data):
    request = HTTPRequest(data)
    return request

def _auth(payload):
    HEADERS =  {'Connection': 'Upgrade',
                'Upgrade': 'websocket',
                'Host': host + ':443',
                'Accept': '*/*',
                'Sec-WebSocket-Key': generate_random_key(),
                'Sec-WebSocket-Version': '13',
                'Content-Length': '0',
                'Content-Type': 'application/json',
                'Transac-Id': '0'
                }

    username = payload['username']
    r = requests.get('https://mediation.tydom.com/mediation/client?mac={}&appli=1'.format(username), headers=HEADERS)

    nonce = r.headers["WWW-Authenticate"].split(',', 3)
    return {'Authorization': build_digest_headers(nonce, payload)}

async def _device_data(payload):
    _vals = ['temperature', 'authorization', 'hvacMode', 'setpoint']
    data = {}
    username = payload['username']
    uri = 'wss://mediation.tydom.com:443/mediation/client?mac={}&appli=1'.format(username)
    async with websockets.connect(uri, extra_headers=_auth(payload), timeout = 5) as websocket:
        msg = '/devices/data'
        str = cmd_prefix + "GET " + msg +" HTTP/1.1\r\nContent-Length: 0\r\nContent-Type: application/json; charset=UTF-8\r\nTransac-Id: 0\r\n\r\n"
        await websocket.send(bytes(str, "ascii"))
        bytes_str = await websocket.recv()
        response = response_from_bytes(bytes_str[len(cmd_prefix):])

        elements = json.loads(response)
        for element in elements:
            for endpoint in element['endpoints']:
                for value in endpoint['data']:
                    if value['name'] in _vals:
                        data['endpoint'] = endpoint['id']
                        data[value['name']] = value['value']
        return data

async def _put_data(endpoint_id, name, value, payload):
    
    username = payload['username']
    host = payload['host']
    
    body = '[{"name":"' + name + '","value":"' + str(value) + '"}]'
    uri = 'wss://{}:443/mediation/client?mac={}&appli=1'.format(host, username)
    async with websockets.connect(uri, extra_headers=_auth(payload), timeout = 5) as websocket:
        rq = cmd_prefix + 'PUT /devices/{}/endpoints/{}/data HTTP/1.1\r\nContent-Length: '.format(str(endpoint_id),str(endpoint_id))+str(len(body))+'\r\nContent-Type: application/json; charset=UTF-8\r\nTransac-Id: 0\r\n\r\n'+body+'\r\n\r\n'
        a_bytes = bytes(rq, 'ascii')
        await websocket.send(a_bytes)
        bytes_str = await websocket.recv()
    response = response_from_bytes(bytes_str[len(cmd_prefix):])

def system_info(payload=None):
    if payload:
        login = payload['username']
        password = payload['password']
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_device_data(payload))

def set_temp(endpoint_id, temp, payload=None):
    if payload:
        username  = payload['username']
        password = payload['password']
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_put_data(endpoint_id, 'setpoint', temp, payload))

def set_hvac(endpoint_id, state, payload=None):
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_put_data(endpoint_id, 'authorization', state, payload))
