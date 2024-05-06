import sys
from pathlib import Path
from socket import gethostname
from typing import Optional, List, Type, TypeVar
from functools import lru_cache

from pydantic import (
    BaseSettings,
    ConstrainedInt,
    DirectoryPath,
    Field,
    FilePath,
    ValidationError,
)


class Port(ConstrainedInt):
    ge = 0
    le = 65535


class ServiceSettings(BaseSettings):
    s3fs_url_protocol: str = "http"
    s3fs_url_host: Optional[str]
    s3fs_url_port: Port = Field(9000)
    s3fs_vol_image_name: str = "127.0.0.1:5000/s3fs-volume-helper"
    s3fs_vol_image_tag: str = "latest"
    s3fs_plugin_alias: str = "s3fs"
    s3fs_helper_network: str = "host"

    host: str = Field(default_factory=gethostname)
    """Set the appropriate listening host name or address value (NOTE: must match SSL cert)"""
    port: Port = Field(3012)
    """Set the appropriate listening port value"""

    cert_path: Optional[FilePath] = None
    """Specify path for a particular SSL certificate file to use"""
    key_path: Optional[FilePath] = None
    """Specify path for a particular SSL private key file to use"""
    ssl_dir: Optional[DirectoryPath] = None
    """Change the base directory when using SSL certificate and key files with default names"""

    object_store_host: str = "minio-proxy"
    """Set hostname for connection to object store"""
    object_store_port: Port = Port(9000)
    """Set port for connection to object store"""

    # TODO: consider making this a pydantic.SecretStr
    object_store_exec_user_name: str
    """Object store user access key"""

    # TODO: consider making this a pydantic.SecretStr
    object_store_exec_user_passwd: str
    """Object store user secret key"""

    redis_host: str = "myredis"
    """Set the host value for making Redis connections"""
    redis_port: Port = Port(6379)
    """Set the port value for making Redis connections"""

    # TODO: consider making this a pydantic.SecretStr
    redis_pass: str = "noaaOwp"
    """Set the password value for making Redis connections"""

    worker_noah_owp_parameters_dir: str = "/dmod/bmi_module_data/noah_owp/parameters"
    """ The 'parameters' directory param for NoahOWP BMI init config generation, from the context of job workers. """

    pycharm_debug: bool = False
    """Activate Pycharm remote debugging support"""

    @classmethod
    def usage(cls, verbose: bool = False) -> str:
        """
        Return a formatted string with service configuration usage information.
        Increase the amount of detail included using the verbose flag.
        """

        header = f"""
Usage: Provide listed service configuration variables as either environment
variables, in a '.env' file, as a 'secret' in {cls.Config.secrets_dir!r}, or as
a mixture of the aforementioned options.

Configuration option names are case insensitive.

Configuration Variable:
"""
        verbose_header = f"""
Usage: Provide listed service configuration variables as either environment
variables, in a '.env' file, as a 'secret' in {cls.Config.secrets_dir!r}, or as
a mixture of the aforementioned options.

Configuration option names are case insensitive.

boolean values are case insensitive.
valid values are:
    0, off, f, false, n, no, 1, on, t, true, y, yes

A '.env' file must be utf-8 encoded and follow syntax rules:
- lines beginning with `#` are treated as comments
- blank lines are ignored
- each line represents a key-value pair. values can optionally be quoted.
  for example:
      PORT=8080
      PORT='8080'
      PORT="8080"
For more in-depth information, see these resources:
- https://docs.docker.com/compose/environment-variables/env-file/#syntax
- https://github.com/theskumar/python-dotenv?tab=readme-ov-file#file-format

A secret's filename must match the name of a configuration variable (case insensitive).
The value of the secret are the contents of the file.

Configuration Source Priority:
1. environment variables
2. variables loaded from a dotenv (.env) file.
3. variables loaded from the secrets directory.
4. default field values

Configuration Variable:
"""
        items = [field_usage(cls, field_name) for field_name in cls.__fields__.keys()]
        config_vars = "\n".join(items)
        if verbose:
            return f"{verbose_header}\n{config_vars}"
        return f"{header}\n{config_vars}"

    class Config(BaseSettings.Config):
        frozen = True
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        # docker secrets location
        secrets_dir = "/run/secrets"
        # field descriptions used for usage documentation
        fields = {
            "host": {
                "description": "Set the appropriate listening host name or address value (NOTE: must match SSL cert)"
            },
            "port": {
                "description": "Set the appropriate listening port value",
            },
            "cert_path": {
                "description": "Specify path for a particular SSL certificate file to use"
            },
            "key_path": {
                "description": "Specify path for a particular SSL private key file to use"
            },
            "ssl_dir": {
                "description": "Change the base directory when using SSL certificate and key files with default names"
            },
            "object_store_host": {
                "description": "Set hostname for connection to object store"
            },
            "object_store_port": {
                "description": "Set port for connection to object store"
            },
            "object_store_exec_user_name": {
                "description": "Object store user access key"
            },
            "object_store_exec_user_passwd": {
                "description": "Object store user secret key"
            },
            "redis_host": {
                "description": "Set the host value for making Redis connections"
            },
            "redis_port": {
                "description": "Set the port value for making Redis connections"
            },
            "redis_pass": {
                "description": "Set the password value for making Redis connections"
            },
            "pycharm_debug": {
                "description": "Activate Pycharm remote debugging support"
            },
        }


class DebugSettings(BaseSettings):
    pycharm_remote_debug_egg: FilePath = Path("/pydevd-pycharm.egg")
    """Set path to .egg file for Python remote debugger util"""
    remote_debug_host: str = "host.docker.internal"
    """Set remote debug host to connect back to debugger"""
    remote_debug_port: Port = Field(55871)
    """Set remote debug port to connect back to debugger"""

    class Config(BaseSettings.Config):
        frozen = True
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        secrets_dir = "/run/secrets"


@lru_cache
def service_settings() -> ServiceSettings:
    return _handle_settings(ServiceSettings)


@lru_cache
def debug_settings() -> DebugSettings:
    return _handle_settings(DebugSettings)


_T = TypeVar("_T", bound=BaseSettings)


def _handle_settings(cls: Type[_T], **kwargs) -> _T:
    try:
        return cls(**kwargs)
    except ValidationError as e:
        usage: List[str] = []
        for err in e.errors():
            field_name: str = err["loc"][0]
            msg = f"{field_usage(ServiceSettings, field_name)}\nError: {err['msg']}\n"
            usage.append(msg)
        error_msg = "\n".join(usage)
        print(f"Service configuration failure: {error_msg}", file=sys.stderr)
        sys.exit(1)


def field_usage(cls: Type[BaseSettings], field_name: str) -> str:
    field_schema = cls.schema(by_alias=False)["properties"][field_name]
    field = cls.__fields__[field_name]

    names = ",".join(name.upper() for name in field_schema["env_names"])
    type_ = field_schema["type"]

    if field.required:
        requirement = " (required)"
    elif field.get_default() is None:
        requirement = " (optional)"
    else:
        default = field.get_default()
        if isinstance(default, str):
            default = repr(default)
        requirement = f" (default={default})"

    description = (
        f"\n\t{field_schema['description']}" if "description" in field_schema else ""
    )

    return f"{names}: {type_}{requirement}{description}"
