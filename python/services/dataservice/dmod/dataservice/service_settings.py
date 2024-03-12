from pydantic import BaseSettings, Field
from typing import Optional
from typing_extensions import Annotated, TypeAlias

Port: TypeAlias = Annotated[int, Field(..., ge=0, le=65535)]


class ServiceSettings(BaseSettings):
    s3fs_url_protocol: str = "http"
    s3fs_url_host: Optional[str]
    s3fs_url_port: Port = 9000
    s3fs_vol_image_name: str = "127.0.0.1:5000/s3fs-volume-helper"
    s3fs_vol_image_tag: str = "latest"
    s3fs_plugin_alias: str = "s3fs"
    s3fs_helper_network: str = "host"


    class Config(BaseSettings.Config):
        frozen = True
        case_sensitive = False
