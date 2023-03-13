"""
Provides functions and classes for consuming websocket connections from a client to this GUI
"""
from .scope import ConcreteScope
from .socket import SocketConsumer
from .pubsub import PubSubConsumer
from .pubsub import EchoSubscriptionConsumer
from .channel import Announcer
from .channel import Notifier