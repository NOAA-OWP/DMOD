"""
Defines the unitilities needed to forward communication from a client, 
through a websocket, to a handler that then echos that information through 
to another service
"""
from .configuration import ForwardingConfiguration
from .consumer import ForwardingSocket
from .views import ForwardingView
