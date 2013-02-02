
import msgpackrpc
from msgpackrpc.transport import tcp

class IDLMockClient(object):
    """ Use this client wrapper to simulate an IDL-generated client class.
        Construct it just like the regular Python RPC Client.
        Instead of .call(method, args), you can use .method(args) directly.
        After using the client, call _summary() to receive a list of what 
        methods have been called.
        Call _failed() to receive a list of remote functions that generated
        an error while calling them.
        After done with prototyping, this class can easily be replaced by
        an IDL-generated client class for the server.
    """

    def __init__(self, address, timeout=10, loop=None, builder=tcp, reconnect_limit=5, pack_encoding='utf-8', unpack_encoding=None):
        self._base = msgpackrpc.Client(address, timeout, loop, builder, reconnect_limit, pack_encoding, unpack_encoding)
        self._list = set()
        self._failedlist = set()

    def __getattr__(self, name):
        def call(*args):
            try:
                self._base.call(name, *args)
            except:
                self._failedlist.add(name)
                raise
        if name[0] == '_':
            raise AttributeError

        self._list.add(name)
        if name[-6:] == "_async":
            return lambda *args:self._base.call_async(name[:-6], *args)
        if name[-7:] == "_notify":
            return lambda *args:self._base.notify(name[:-7], *args)
        return call

    def _summary(self):
        return self._list

    def _failed(self):
        return self._failedlist
