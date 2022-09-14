"""
Provides the implementation of a class that can handle communication to and from the evaluation service
"""

import dmod.communication as communication
import dmod.communication.client as communication_client

from .duplex import DuplexRequestHandler
from .duplex import ListenerMixin
from .duplex import RepeatMixin


class EvaluationRequestHandler(DuplexRequestHandler, ListenerMixin, RepeatMixin):
    """
    Handles communication to and from the Evaluation Service
    """
    @classmethod
    def get_target_service(cls) -> str:
        """
        Returns:
            A human friendly name for what service this handler should be targetting
        """
        return "Evaluation Service"

    def _construct_client(self) -> communication.InternalServiceClient:
        return communication_client.EvaluationServiceClient(self.service_url, self.ssl_directory)
