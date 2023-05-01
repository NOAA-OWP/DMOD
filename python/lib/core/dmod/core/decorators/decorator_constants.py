

INITIALIZER_ATTRIBUTE = "initializer"
"""The name of the attribute stating that the owner should be used for initialization"""

ADDITIONAL_PARAMETER_ATTRIBUTE = "additional_parameter"
"""
The name of the attribute stating that the owner should be used to determine additional parameters for services 
to send to handlers
"""


SOCKET_HANDLER_ATTRIBUTE = "socket_handler"
"""
The name of the attribute stating that a service should be able to use the owner to consume new websocket connections
"""

MESSAGE_HANDLER_ATTRIBUTE = "message_handler"
"""
The name of the attribute stating that the owner can consume messages that come through a websocket
"""

PRODUCER_MESSAGE_HANDLER_ATTRIBUTE = "producer_handler"
"""
The name of the attribute stating that the owner can produce messages on its on and send results through a socket
"""

SERVER_MESSAGE_HANDLER_ATTRIBUTE = "server_handler"
"""
The name of the attribute stating the the owner should consume messages from a websocket server
"""

CLIENT_MESSAGE_HANDLER_ATTRIBUTE = "client_handler"
"""
The name of the attribute stating that the owner should consume messages from a websocket client
"""

MESSAGE_TYPE_ATTRIBUTE = "message_type"
"""
Attribute indicating what sort of message a socket handler should be able to consume
"""

HANDLER_ACTION_ATTRIBUTE = "action"
"""
The name of an attribute indicating that something is an action
"""

DESCRIPTION_ATTRIBUTE = "description"
"""
The name of an attribute indicating a helpful description
"""
