
class Loop(object):
    """\
    An I/O loop class which wraps the Tornado's ioloop.
    """

    @staticmethod
    def instance():
        from tornado import ioloop
        return Loop(ioloop.IOLoop())

    def __init__(self, loop=None):
        """\
        Creates a wrapper around the Tornado IOLoop structure
        Pass in an existing IOLoop if you want, otherwise it will use its own
        """
        from tornado import ioloop
        self._ioloop = loop or ioloop.IOLoop()
        self._periodic_callback = None

    def start(self):
        """\
        Starts the Tornado's ioloop if it's not running.
        """
        if not self._ioloop.running():
            self._ioloop.start()

    def stop(self):
        """\
        Stops the Tornado's ioloop if it's running.
        """
        if self._ioloop.running():
            try:
                self._ioloop.stop()
            except:
                return

    def attach_periodic_callback(self, callback, callback_time):
        if self._periodic_callback is not None:
            self.detach_periodic_callback()

        from tornado import ioloop
        self._periodic_callback = ioloop.PeriodicCallback(callback, callback_time, self._ioloop)
        self._periodic_callback.start()

    def detach_periodic_callback(self):
        if self._periodic_callback is not None:
            self._periodic_callback.stop()
        self._periodic_callback = None
