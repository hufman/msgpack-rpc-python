import msgpack

from msgpackrpc import Loop
from msgpackrpc import message
from msgpackrpc import session
from msgpackrpc.transport import tcp

class Server(session.Session):
    """\
    Server is usaful for MessagePack RPC Server.
    """

    def __init__(self, dispatcher, loop=None, builder=tcp, pack_encoding='utf-8', unpack_encoding=None):
        self._loop = loop or Loop()
        self._builder = builder
        self._encodings = (pack_encoding, unpack_encoding)
        self._listeners = []
        self._dispatcher = dispatcher

    def listen(self, address):
        listener = self._builder.ServerTransport(address, self._encodings)
        listener.listen(self)
        self._listeners.append(listener)

    def notify(self, method, *args):
        def callback():
            self._loop.stop()
        for listener in self._listeners:
             listener.send_message([message.NOTIFY, method, args], callback=callback)
        self._loop.start()

    def start(self):
        self._loop.start()

    def stop(self):
        self._loop.stop()

    def close(self):
        for listener in self._listeners:
            listener.close()

