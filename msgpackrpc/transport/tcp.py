import msgpack
import msgpackrpc.message
from msgpackrpc.error import RPCError, TransportError

import socket
import errno

class BaseSocket(object):
    def __init__(self, socket, encodings):
        self._socket = socket
        self._outchunks = []
        self._callback = None
        self._packer = msgpack.Packer(encoding=encodings[0], default=lambda x: x.to_msgpack())
        self._unpacker = msgpack.Unpacker(encoding=encodings[1], use_list=False)

    def close(self):
        self._transport._loop.detach_socket(self._socket)
        self._socket.close()

    def _try_send(self, sock):
        while self._outchunks:
            try:
                sent = self._socket.send(self._outchunks[0])
                if sent == -1:
                    self.on_error(sock)
                    return
                self._outchunks[0] = self._outchunks[0][sent:]
                if len(self._outchunks[0]) == 0:
                    self._outchunks.pop(0)
            except socket.error as e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    break
                else:
                    self.on_error(sock)
                    return
        # when everything is done, disconnect the send loop
        self._transport._loop.detach_socket(self._socket)
        self._transport._loop.attach_socket(self._socket, self.on_available, None, self.on_error)
        if self._callback:
            self._callback()

    def send_message(self, message, callback=None):
        CHUNK_SIZE = 128 * 1024
        message = self._packer.pack(message)
        for i in range(0, len(message), CHUNK_SIZE):
            self._outchunks.append(message[i:i + CHUNK_SIZE])
        self._callback = callback
        self._transport._loop.detach_socket(self._socket)
        self._transport._loop.attach_socket(self._socket, self.on_available, self._try_send, self.on_error)

    def on_read(self, data):
        self._unpacker.feed(data)
        for message in self._unpacker:
            self.on_message(message)

    def on_message(self, message, *args):
        msgsize = len(message)
        if msgsize != 4 and msgsize != 3:
            raise RPCError("Invalid MessagePack-RPC protocol: message = {0}".format(message))

        msgtype = message[0]
        if msgtype == msgpackrpc.message.REQUEST:
            self.on_request(message[1], message[2], message[3])
        elif msgtype == msgpackrpc.message.RESPONSE:
            self.on_response(message[1], message[2], message[3])
        elif msgtype == msgpackrpc.message.NOTIFY:
            self.on_notify(message[1], message[2])
        else:
            raise RPCError("Unknown message type: type = {0}".format(msgtype))

    def on_request(self, msgid, method, param):
        raise NotImplementedError("on_request not implemented");

    def on_response(self, msgid, error, result):
        raise NotImplementedError("on_response not implemented");

    def on_notify(self, method, param):
        raise NotImplementedError("on_notify not implemented");


class ClientSocket(BaseSocket):
    def __init__(self, transport, encodings):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setblocking(False)
        BaseSocket.__init__(self, self._socket, encodings)
        self._transport = transport
        self._transport._loop.attach_socket(self._socket, self.on_available, self.on_writable, self.on_error)

    def connect(self):
        self._connecting = True
        try:
            self._socket.connect(self._transport._address.unpack())
        except socket.error as e:
            if e.args[0] not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                self.on_error()

    def on_connect(self):
        self._connecting = False
        self._transport.on_connect(self)

    def on_connect_failed(self):
        self._transport.on_connect_failed(self)

    def on_available(self, sock):
        try:
            data = sock.recv(1024)
        except socket.error as e:
            if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                self.on_error(sock)
                return
        if data:
            self.on_read(data)
        else:
            self.on_error(sock)

    def on_writable(self, socket):
        """ Called when the socket becomes connected and ready to write """
        if self._connecting:
            self.on_connect()

    def on_error(self, socket):
        if self._connecting:
            self.on_connect_failed()
            return
        self.close()
        self.on_close()

    def on_close(self):
        self._transport.on_close(self)

    def on_response(self, msgid, error, result):
        self._transport._session.on_response(msgid, error, result)

class ClientTransport(object):
    def __init__(self, session, address, reconnect_limit, encodings=('utf-8', None)):
        self._session = session
        self._address = address
        self._encodings = encodings
        self._reconnect_limit = reconnect_limit;
        self._loop = self._session._loop

        self._connecting = 0
        self._pending = []
        self._sockets = []
        self._closed  = False

    def send_message(self, message, callback=None):
        if len(self._sockets) == 0:
            if self._connecting == 0:
                self.connect()
                self._connecting = 1
            self._pending.append((message, callback))
        else:
            sock = self._sockets[0]
            sock.send_message(message, callback)

    def connect(self):
        client = ClientSocket(self, self._encodings)
        client.connect();

    def close(self):
        for sock in self._sockets:
            sock.close()

        self._connecting = 0
        self._pending = []
        self._sockets = []
        self._closed  = True

    def on_connect(self, sock):
        self._sockets.append(sock)
        for pending, callback in self._pending:
            sock.send_message(pending, callback)
        self._pending = []

    def on_connect_failed(self, sock):
        if self._connecting < self._reconnect_limit:
            self.connect()
            self._connecting += 1
        else:
            self._connecting = 0
            self._pending = []
            self._session.on_connect_failed(TransportError("Retry connection over the limit"))

    def on_close(self, sock):
        # Avoid calling self.on_connect_failed after self.close called.
        if self._closed:
            return

        if sock in self._sockets:
            self._sockets.remove(sock)
        else:
            # Tornado does not have on_connect_failed event.
            self.on_connect_failed(sock)


class ServerSocket(BaseSocket):
    def __init__(self, socket, listener, transport, encodings):
        BaseSocket.__init__(self, socket, encodings)
        self._listener = listener
        self._transport = transport
        self._transport._loop.attach_socket(self._socket, self.on_available, None, self.on_error)

    def on_available(self, sock):
        data = None
        try:
            data = sock.recv(1024)
        except socket.error as e:
            if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                self.on_error()
                return

        if data:
            self.on_read(data)
        else:
            self.on_error(sock)

    def on_error(self, socket):
        self.close()
        self.on_close()

    def on_close(self):
        self._listener.on_close(self)

    def on_request(self, msgid, method, param):
        self._transport._server.on_request(self, msgid, method, param)

    def on_notify(self, method, param):
        self._transport._server.on_notify(method, param)

class ServerListener(object):
    def __init__(self, transport):
        self._transport = transport	# parent transport
        self._socket = None		# listening socket
        self._sockets = []		# connected sockets

    def listen(self, address):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("0.0.0.0", address.port))
        self._socket.setblocking(0)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.listen(5)
        self._transport._loop.attach_socket(self._socket, self.accept, None, None)

    def accept(self, socket):
        client,address = socket.accept()
        self._sockets.append(ServerSocket(client, self, self._transport, self._transport._encodings))

    def on_close(self, serverSocket):
        if serverSocket in self._sockets:
            self._sockets.remove(serverSocket)

    def close(self):
        for sock in self._sockets:
            sock.close()
        self._sockets = []
        self._socket.close()

class ServerTransport(object):
    def __init__(self, address, encodings=('utf-8', None)):
        self._address = address;
        self._encodings = encodings

    def listen(self, server):
        self._server = server;
        self._loop = self._server._loop
        self._listener = ServerListener(self)
        self._listener.listen(self._address)

    def close(self):
        self._listener.close()
