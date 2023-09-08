from dmod.core.serializable import Serializable
from pathlib import Path
from typing import Optional
from pydantic import Field, validator


class ConnectionConfig(Serializable):

    active: bool = Field(True, description="Whether this configured connection should be active and initialized")
    endpoint_protocol: str = Field(description="The protocol in this config", alias="protocol")
    endpoint_host: str = Field(description="The configured hostname", alias="hostname")
    endpoint_port: int = Field(description="The configured host port", alias="port")
    cafile: Optional[Path] = Field(None, description="Optional path to CA certificates PEM file.", alias="pem")
    capath: Optional[Path] = Field(None, description="Optional path to directory containing CA certificates PEM files.",
                                   alias="ssl-dir")
    use_default_context: bool = False


class ClientConfig(Serializable):

    request_service: ConnectionConfig = Field(description="The config for connecting to the request service",
                                              alias="request-service")
    data_service: Optional[ConnectionConfig] = Field(None, description="The config for connecting to the data service",
                                                     alias="data-service")

    @validator("request_service")
    def validate_request_service_connection_active(cls, value):
        if not value.active:
            raise RuntimeError(f"{cls.__name__} must have request service config set to 'active'!")
        return value
