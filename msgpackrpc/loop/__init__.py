"""
The loop submodule is used to hold Runloop adapters
Each Runloop adapter should implement these methods::

    class Loop(object):
        @staticmethod
        def instance():
            return Loop()

        def __init__(self, loop=None):
            # Use the provided loop if possible, or create a new one

        def start(self):
            # Run the loop until stop() is called
            # This method must block until stop() is called

        def stop(self):
            # Stop the loop from running, 
            # allowing the start() method to return 

        def attach_periodic_callback(self, callback, callback_time):
            # Insert the given callback into the runloop
            # It should be scheduled in a repeating fashion, not just once
            # If an existing periodic_callback is in place, replace it
            # @param callback_time is in milliseconds

        def detach_periodic_callback(self):
            # Stop an existing periodic callback and remove it

        def attach_socket(self, socket, incallback, outcallback=None, errcallback=None):
            # Insert the given socket into the runloop
            # Calls incallback when the socket can be read
            # Calls outcallback when the socket can be written to
            # Calls errcallback when the socket has an error

        def detach_socket(self, socket):
            # Detaches the given socket from the runloop
"""

from . import tornadoloop as tornado
from . import glibloop as glib
del(tornadoloop)
del(glibloop)
