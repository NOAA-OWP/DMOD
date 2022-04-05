import yaml
from abc import ABC, abstractmethod
from pathlib import Path


class ClientConfig(ABC):
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

    def __init__(self, client_config_file: Path, *args, **kwargs):
        super(ClientConfig, self).__init__(*args, **kwargs)
        self._config_file = client_config_file
        with self._config_file.open() as file:
            self._backing_config = yaml.safe_load(file)
            self._requests_hostname = self._backing_config[self._CONFIG_KEY_REQUEST_SERVICE][self._CONFIG_KEY_HOSTNAME]
            self._requests_port = self._backing_config[self._CONFIG_KEY_REQUEST_SERVICE][self._CONFIG_KEY_PORT]
            self._requests_endpoint_uri = 'wss://{}:{}'.format(self._requests_hostname, self._requests_port)
            self._requests_ssl_dir = Path(self._backing_config[self._CONFIG_KEY_REQUEST_SERVICE][self._CONFIG_KEY_SSL_DIR])
            if not self._requests_ssl_dir.is_dir():
                raise RuntimeError(
                    "Non-existing request service SSL directory configured ({})".format(self._requests_ssl_dir))

    @property
    def config_file(self) -> Path:
        return self._config_file

    @property
    def requests_endpoint_uri(self) -> str:
        return self._requests_endpoint_uri

    @property
    def requests_ssl_dir(self) -> Path:
        return self._requests_ssl_dir

    def print_config(self):
        print(self._config_file.read_text())
