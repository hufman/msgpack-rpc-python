import sys
import msgpackrpc

from msgpackrpc.transport import tcp as transport
from msgpackrpc.loop import tornado as loop

if '--transport' in sys.argv:
    index = sys.argv.index('--transport')
    transport = __import__("msgpackrpc.transport.%s"%sys.argv[index+1], fromlist=["msgpackrpc.transport"])

if '--loop' in sys.argv:
    index = sys.argv.index('--loop')
    loop = __import__("msgpackrpc.loop.%sloop"%sys.argv[index+1], fromlist=["msgpackrpc.loop"])

class SumServer(object):
    def sum(self, x, y):
        return x + y

server = msgpackrpc.Server(SumServer(), loop=loop.Loop(), builder=transport)
server.listen(msgpackrpc.Address("localhost", 18800))
server.start()
