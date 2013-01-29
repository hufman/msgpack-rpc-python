#!/usr/bin/python

import msgpackrpc
class Server(object):
    def ping(self):
        return True
    def sum(self, a, b):
        return a + b
    def crash(self):
        return 1/0

import sys
port = None
if len(sys.argv)>1:
    port = int(sys.argv[1])

loop = msgpackrpc.loop.glib.Loop()
from msgpackrpc.transport import tcp
server=msgpackrpc.Server(Server(), loop=loop, builder=tcp)
server.listen(msgpackrpc.Address("0.0.0.0", port or 18800))

import glib

while True:
    glib.MainLoop().get_context().iteration(True)
