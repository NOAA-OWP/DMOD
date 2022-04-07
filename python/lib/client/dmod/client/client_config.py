import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class ClientConfig(ABC):
    _CONFIG_KEY_DATA_SERVICE = 'data-service'
    _CONFIG_KEY_HOSTNAME = 'hostname'
    _CONFIG_KEY_PORT = 'port'
    _CONFIG_KEY_REQUEST_SERVICE = 'request-service'
    _CONFIG_KEY_SSL_DIR = 'ssl-dir'

    def __init__(self, *args, **kwargs):
        super(ClientConfig, self).__init__(*args, **kwargs)

    @property
    @abstractmethod
    def config_file(self) -> Path:
        pass

    @property
    @abstractmethod
    def dataservice_endpoint_uri(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def dataservice_ssl_dir(self) -> Optional[Path]:
        pass

    @property
    @abstractmethod
    def requests_endpoint_uri(self) -> str:
        pass

    @property
    @abstractmethod
    def requests_ssl_dir(self) -> Path:
        pass

    @abstractmethod
    def print_config(self):
        pass


class YamlClientConfig(ClientConfig):

    @classmethod
    def generate_endpoint_uri(cls, hostname: str, port: int):
        return 'wss://{}:{}'.format(hostname, port)

    @classmethod
    def get_service_ssl_dir(cls, backing_config: dict, service_key: str):
        dir_path = Path(backing_config[service_key][cls._CONFIG_KEY_SSL_DIR])
        if dir_path.is_dir():
            return dir_path
        else:
            raise RuntimeError("Non-existing {} SSL directory configured ({})".format(service_key, dir_path))

    def __init__(self, client_config_file: Path, *args, **kwargs):
        super(ClientConfig, self).__init__(*args, **kwargs)
        self._config_file = client_config_file
        with self._config_file.open() as file:
            self._backing_config = yaml.safe_load(file)
        self._requests_endpoint_uri = self.generate_endpoint_uri(self.requests_hostname, self.requests_port)
        self._requests_ssl_dir = self.get_service_ssl_dir(self._backing_config, self._CONFIG_KEY_REQUEST_SERVICE)

        self._dataservice_endpoint_uri = None
        self._dataservice_ssl_dir = None

    @property
    def config_file(self) -> Path:
        return self._config_file

    @property
    def dataservice_endpoint_uri(self) -> Optional[str]:
        if self._dataservice_endpoint_uri is None and self.dataservice_hostname is not None:
            self._dataservice_endpoint_uri = self.generate_endpoint_uri(self.dataservice_hostname, self.dataservice_port)
        return self._dataservice_endpoint_uri

    @property
    def dataservice_hostname(self) -> Optional[str]:
        if self._CONFIG_KEY_DATA_SERVICE in self._backing_config:
            return self._backing_config[self._CONFIG_KEY_DATA_SERVICE][self._CONFIG_KEY_HOSTNAME]
        else:
            return None

    @property
    def dataservice_port(self) -> Optional[int]:
        if self._CONFIG_KEY_DATA_SERVICE in self._backing_config:
            return self._backing_config[self._CONFIG_KEY_DATA_SERVICE][self._CONFIG_KEY_PORT]
        else:
            return None

    @property
    def dataservice_ssl_dir(self) -> Optional[Path]:
        if self._dataservice_ssl_dir is None and self._CONFIG_KEY_DATA_SERVICE in self._backing_config:
            self._dataservice_ssl_dir = self.get_service_ssl_dir(self._backing_config, self._CONFIG_KEY_DATA_SERVICE)
        return self._dataservice_ssl_dir

    @property
    def requests_endpoint_uri(self) -> str:
        return self._requests_endpoint_uri

    @property
    def requests_hostname(self) -> str:
        return self._backing_config[self._CONFIG_KEY_REQUEST_SERVICE][self._CONFIG_KEY_HOSTNAME]

    @property
    def requests_port(self) -> int:
        return self._backing_config[self._CONFIG_KEY_REQUEST_SERVICE][self._CONFIG_KEY_PORT]

    @property
    def requests_ssl_dir(self) -> Path:
        return self._requests_ssl_dir

    def print_config(self):
        print(self._config_file.read_text())
