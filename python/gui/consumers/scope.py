"""
Put a module wide description here
"""
import typing

from urllib.parse import parse_qs



class ConcreteScope:
    """
    A typed object with clear attributes for everything expected in a 'scope' dictionary for websockets
    """
    def __init__(self, scope: dict):
        from django.contrib.sessions.backends.db import SessionStore
        from django.contrib.auth.models import User

        self.__scope = scope
        self.__type: str = scope.get("type")
        self.__path: str = scope.get("path")
        self.__raw_path: bytes = scope.get("raw_path")
        self.__headers: typing.List[typing.Tuple[bytes, bytes]] = scope.get("headers", list())
        self.__query_arguments: typing.Dict[str, typing.List[str]] = parse_qs(scope.get("query_string", ""))
        self.__client_host: str = scope.get("client")[0] if 'client' in scope and len('scope') > 0 else None
        self.__client_port: str = scope.get("client")[-1] if 'client' in scope and len('scope') > 1 else None
        self.__server_host: str = scope.get("server")[0] if 'server' in scope and len('scope') > 0 else None
        self.__server_port: str = scope.get("server")[-1] if 'server' in scope and len('scope') > 1 else None
        self.__asgi: typing.Dict[str, str] = scope.get("asgi", dict())
        self.__cookies: typing.Dict[str, str] = scope.get("cookies", dict())
        self.__session: typing.Optional[SessionStore] = scope.get("session")
        self.__user: typing.Optional[User] = scope.get("user")
        self.__path_remaining: str = scope.get("path_remaining")

        if 'url_route' in scope and 'args' in scope['url_route']:
            self.__arguments: typing.Tuple[str] = scope['url_route']['args'] or tuple()
        else:
            self.__arguments: typing.Tuple[str] = tuple()

        if 'url_route' in scope and 'kwargs' in scope['url_route']:
            self.__kwargs: typing.Dict[str, str] = scope['url_route']['kwargs'] or dict()
        else:
            self.__kwargs: typing.Dict[str, str] = dict()

    @property
    def type(self) -> typing.Optional[str]:
        """
        The type of object this scope is for
        """
        return self.__type

    @property
    def path(self) -> typing.Optional[str]:
        """
        The path on the server that brought the request here
        """
        return self.__path

    @property
    def raw_path(self) -> typing.Optional[bytes]:
        """
        The raw path on the server that brought the request here
        """
        return self.__raw_path

    @property
    def headers(self) -> typing.List[typing.Tuple[bytes, bytes]]:
        """
        A list of HTTP headers that came along with the request
        """
        return self.__headers

    @property
    def query_arguments(self) -> typing.Dict[str, typing.List[str]]:
        """
        All arguments passed via query string
        """
        return self.__query_arguments

    @property
    def client(self) -> typing.Optional[str]:
        """
        The address for the client that connected to the socket
        """
        client_address: str = ""
        if self.__client_host:
            client_address += self.__client_host

            if self.__client_port:
                client_address += f":{self.__client_port}"

        return client_address

    @property
    def client_host(self) -> typing.Optional[str]:
        """
        The host for the client that connected to the socket
        """
        return self.__client_host

    @property
    def client_port(self) -> typing.Optional[str]:
        """
        The port for the client that connected to the socket
        """
        return self.__client_port

    @property
    def server(self) -> str:
        """
        The address for the server that received the request for a socket
        """
        server_address: str = ""

        if self.__server_host:
            server_address += self.__server_host

            if self.__server_port:
                server_address += f":{self.__server_port}"

        return server_address

    @property
    def server_host(self) -> typing.Optional[str]:
        """
        The host name of the server that received the request for a socket
        """
        return self.__server_host

    @property
    def server_port(self) -> typing.Optional[str]:
        """
        The port of the server that received the request for a socket
        """
        return self.__server_port

    @property
    def asgi(self) -> typing.Dict[str, str]:
        """
        asgi settings for the gateway

        Expect something like {'version': '3.0'}
        """
        return self.__asgi

    @property
    def cookies(self) -> typing.Dict[str, str]:
        """
        All cookies passed along from the client
        """
        return self.__cookies

    @property
    def session(self):
        """
        Session data for the connected user (if there is one)
        """
        return self.__session

    @property
    def user(self):
        """
        The user (anonymous or logged in) that tried to make the connection
        """
        return self.__user

    @property
    def path_remaining(self) -> str:
        return self.__path_remaining

    @property
    def arguments(self) -> typing.Tuple[str, ...]:
        """
        Arguments passed into the URL route
        """
        return self.__arguments

    @property
    def keyword_arguments(self) -> typing.Dict[str, str]:
        """
        Keyword arguments passed into the URL route
        """
        return self.__kwargs

    def get(self, key, default: typing.Any = None) -> typing.Any:
        """
        Call the underlying scope dictionary's `get` function

        Args:
            key: The key for the value to get
            default: A value to return if the key is not present

        Returns:
            The value if the key is present, `None` otherwise
        """
        return self.__scope.get(key, default)

    def __getitem__(self, key):
        return self.__scope[key]

    def keys(self) -> typing.KeysView:
        """
        All keys for the underlying scope dictionary
        """
        return self.__scope.keys()

    def values(self) -> typing.ValuesView:
        """
        All values for the underlying scope dictionary
        """
        return self.__scope.values()

    def items(self) -> typing.ItemsView:
        """
        All items in the underlying scope dictionary, packaged into 2-tuples like (key, value).
        """
        return self.__scope.items()