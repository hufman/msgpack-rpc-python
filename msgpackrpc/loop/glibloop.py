import collections

class Loop(object):
    """\
    An I/O loop class which wraps Glib's ioloop.
    """

    @staticmethod
    def instance():
        return Loop()

    def __init__(self, loop=None):
        import glib
        glib.threads_init()
        self._glib = glib
        self._sockets = {}
        self._stoppings = collections.deque()
        self._running = False
        self._periodic_callback = None
        pass

    def start(self):
        """\
        Block on the glib loop until told to stop
        """
        if not self._running:
           self._running = True
        while self._running:
            self._glib.MainLoop().get_context().iteration(True)
        contents = True
        while contents:
            try:
                self._glib.source_remove(self._stoppings.pop())
            except IndexError:
                contents = False
        
    def stop(self):
        """\
        Stop blocking on the glib loop
        """
        self._running = False
        id = self._glib.idle_add(lambda:False)
        self._stoppings.append(id)

    def attach_periodic_callback(self, callback, callback_time):
        if self._periodic_callback is not None:
            self.detach_periodic_callback()

        self._periodic_callback = self._glib.timeout_add(callback_time, callback)

    def detach_periodic_callback(self):
        if self._periodic_callback is not None:
            self._glib.source_remove(self._periodic_callback)
        self._periodic_callback = None

    def attach_socket(self, socket, incallback, outcallback=None, errcallback=None):
        def inwrapped(source, condition):
            incallback(socket)
            return True
        def outwrapped(source, condition):
            outcallback(socket)
            return True
        def errwrapped(source, condition):
            errcallback(socket)
            return False

        fd = socket.fileno()
        if fd not in self._sockets.keys():
            self._sockets[fd] = []
        if incallback:
            self._sockets[fd].append(self._glib.io_add_watch(socket, self._glib.IO_IN | self._glib.IO_PRI, inwrapped))
        if outcallback:
            self._sockets[fd].append(self._glib.io_add_watch(socket, self._glib.IO_OUT, outwrapped))
        if errcallback:
            self._sockets[fd].append(self._glib.io_add_watch(socket, self._glib.IO_ERR, errwrapped))

    def detach_socket(self, socket):
        fd = socket.fileno()
        if fd in self._sockets.keys():
            for eventid in self._sockets[fd]:
                self._glib.source_remove(eventid)
        del self._sockets[fd]
