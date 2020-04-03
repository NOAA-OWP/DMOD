from abc import ABC
from os import getenv
from redis import Redis
from time import sleep as time_sleep
from typing import Optional
from .keynamehelper import KeyNameHelper


class RedisBacked(ABC):
    """
    Abstract interface for classes that use a Redis backend store.

    Class has some functionality tailored to run within a Docker container (e.g., the default ``parent_directory`` for
    ::method:`get_redis_pass`, which is the default directory for Docker secrets inside containers), but should be fully
    compatible with use outside of it.
    """

    _DEFAULT_DOCKER_SECRET_REDIS_PASS = 'myredis_pass'
    _DEFAULT_DOCKER_SECRETS_CONTAINER_DIRECTORY = '/run/secrets/'
    _DEFAULT_REDIS_HOST = 'redis'
    _DEFAULT_REDIS_PASS = ''
    _DEFAULT_REDIS_PORT = 6379
    _ENV_NAME_DOCKER_SECRET_REDIS_PASS = 'DOCKER_SECRET_REDIS_PASS'
    _ENV_NAME_REDIS_HOST = 'REDIS_HOST'
    _ENV_NAME_REDIS_PASS = 'REDIS_PASS'
    _ENV_NAME_REDIS_PORT = 'REDIS_PORT'

    @classmethod
    def _init_redis_client(cls, host: str, port: int, passwd: str, max_attempts: int, db_num: int) -> Optional[Redis]:
        """
        Actual logic for attempts to initialize Redis client.

        Intent is for this to only be used during by object initializer.  Other than keeping code clean, the goal is to
        have something easily separable from the rest of initializer.  The allows for better isolation of logic during
        testing. As such, there is limited sanity checking of parameters.

        Parameters
        ----------
        host : str
            The Redis host.

        port : int
            The listening port of the Redis host.

        passwd : str
            The password to authenticate with the Redis host.

        max_attempts : int
            The max attempts before returning.

        db_num : int
            The Redis ``db`` parameter value to use.

        Returns
        -------
        Optional[Redis]
            An initialize Redis client object, or ``None`` if all attempts failed.
        """
        n = 0
        while n <= max_attempts:
            # Sleep for one second on any retries, but not the first attempt.
            if n == 0:
                time_sleep(1)
            try:
                return Redis(host=host, port=port, db=db_num, decode_responses=True, password=passwd)
            # FIXME except only redis failures here
            except:
                # TODO: implement some kind of logging
                #logging.debug("redis connection error")
                pass
            n += 1
        return None

    @classmethod
    def get_docker_secret_name_for_redis_pass(cls) -> str:
        """
        Get the name of the Docker secret for securely storing the Redis password.

        Method returns either the value in an environmental variable ::attribute:`_ENV_NAME_DOCKER_SECRET_REDIS_PASS` or
        a hard-coded default if the former is not set.

        Returns
        -------
        str
            The name of the Docker secret for securely storing the Redis password.
        """
        return getenv(cls._ENV_NAME_DOCKER_SECRET_REDIS_PASS, cls._DEFAULT_DOCKER_SECRET_REDIS_PASS)

    @classmethod
    def get_docker_secrets_directory(cls) -> str:
        """
        Get (as a string) the path to the in-container Docker secrets directory.

        Returns
        -------
        str
            The path to the in-container Docker secrets directory, represented as a string.
        """
        return cls._DEFAULT_DOCKER_SECRETS_CONTAINER_DIRECTORY

    @classmethod
    def get_redis_host(cls) -> str:
        """
        Get the value to use for the Redis host parameter, attempting first to read this from an environmental variable,
        then falling back to a hard-coded default.

        Returns
        -------
        str
            The value to use for the Redis host parameter.
        """
        return getenv(cls._ENV_NAME_REDIS_HOST, cls._DEFAULT_REDIS_HOST)

    @classmethod
    def get_redis_pass(cls, basename: Optional[str] = None, parent_directory: Optional[str] = None) -> str:
        """
        Get and return the Redis password value, first attempting to read from a file, (e.g., a Docker secret in-memory
        FS mount), then falling back to using the value of an environmental variable, and finally using a hard-coded
        default.

        Method first attempts to read the represented file, if it exists, with the basename and parent directory given
        as string parameters.  If no basename is given or the value passed is ``None``, ``basename`` is set to the value
        returned by ::method:`get_docker_secret_name_for_redis_pass`.  Similarly, ``parent_directory`` is replaced by
        ::method:`get_docker_secrets_directory` when ``None``.

        If the file cannot be read, or it can be read but is empty, the method attempts to return the value of the
        environmental variable with name equal to ::attribute:`_ENV_NAME_REDIS_PASS`.  It falls back to returning a
        hard-coded value if that env var is not set.

        Parameters
        ----------
        basename : Optional[str]
            The basename of the file to read containing the password, defaulting to the value returned by
            ::method:`get_docker_secret_name_for_redis_pass` when implicitly or explicitly set to ``None``.

        parent_directory : Optional[str]
            The parent directory of the file to read containing the password, defaulting to the value returned by
            ::method:`get_docker_secrets_directory` when implicitly or explicitly set to ``None``.

        Returns
        -------
        str
            The string to use as the password in Redis connections.
        """
        if basename is None:
            basename = cls.get_docker_secret_name_for_redis_pass()
        if parent_directory is None:
            parent_directory = cls.get_docker_secrets_directory()

        password_filename = parent_directory + '/' + basename
        try:
            with open(password_filename, 'r') as redis_pass_secret_file:
                content = redis_pass_secret_file.read()
                if len(content) < 1:
                    raise ValueError
                else:
                    return content
        except:
            pass
        # Fall back to env if no secrets file, further falling back to default if no env value
        return getenv(cls._ENV_NAME_REDIS_PASS, cls._DEFAULT_REDIS_PASS)

    @classmethod
    def get_redis_port(cls) -> int:
        """
        Get the value to use for the Redis port parameter, attempting first to read this from an environmental variable,
        then falling back to a hard-coded default.

        Returns
        -------
        int
            The value to use for the Redis port parameter.
        """
        try:
            return int(getenv(cls._ENV_NAME_REDIS_PORT, cls._DEFAULT_REDIS_PORT))
        except:
            return cls._DEFAULT_REDIS_PORT

    def __init__(self, redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None, max_redis_init_attempts: int = 5, **kwargs):
        """
        Initialize an instance by creating an open Redis connection object using the given parameters or suitable
        replacements for those set to ``None``.

        During initialization, the parameters for Redis host, port, and/or password will have a value of ``None``
        replaced with the returned value from ::method:`get_redis_host`, ::method:`get_redis_port`, and/or
        ::method:`get_redis_pass` respectively.

        Once the parameter values are set, the method will attempt to initialize a ::class:`Redis` connection object
        and store it in the backing attribute for the ::attribute:`redis` property.  It will optionally retry if
        attempts encounter raised errors, sleeping for 1 second after each attempt, up to the given maximum number of
        attempts. By default, the maximum number of attempts is ``5`` if not provided.  This value is also used if a
        non-integer argument is passed (meaning also that the argument cannot be cast to an integer).  Additionally,
        argument values of less than one will still be tried once, though not re-tried.

        Objects also have their ::attribute:`keynamehelper` attribute set at initialization to the value returned by
        ::method:``KeyNameHelper.get_default_instance``.

        Instances can be initialized in either ``prod``, ``local``, or ``dev`` operational modes, via setting a ``type``
        keyword arg to one of those values.  This affects the Redis DB index that is used for the connection (see its
        ``db`` keyword arg) and whether the object removes all the keys within that Redis DB index upon initialization.
        For ``prod``, ``local``, or ``dev``, these are ``(0, False)``, ``(4, False)``, and ``(5, True)`` respectively.
        The DB index value is tracked in the "private" ::attribute:`_db_num` attribute.

        Parameters
        ----------
        redis_host : Optional[str]
            The value to use, when given, for ``host`` parameter of the Redis connection.

        redis_port : Optional[int]
            The value to use, when given, for ``port`` parameter of the Redis connection.

        redis_pass : Optional[str]
            The value to use, when given, for ``password`` parameter of the Redis connection.

        max_redis_init_attempts : int
            The maximum number of times to attempt opening a Redis connection before allowing raised exceptions to pass
            through uncaught, equal to ``5`` by default.

        kwargs
            Keyed init parameters as described in *Keyword Args* section.

        Keyword Args
        ------------
        type : str
            The object's operational mode (``prod``, ``local``, or ``dev``, with ``prod`` being the implied default).

        """
        # initialize Redis client
        if redis_host is None:
            redis_host = self.get_redis_host()
        if redis_port is None:
            redis_port = self.get_redis_port()
        if redis_pass is None:
            redis_pass = self.get_redis_pass()

        # Make sure max_redis_init_attempts is sane, both in type ...
        if not isinstance(max_redis_init_attempts, int):
            try:
                max_redis_init_attempts = int(max_redis_init_attempts)
            except:
                # Assume use default if something bogus was passed
                max_redis_init_attempts = 5
        # ... and it value (i.e., always try at least once)
        if max_redis_init_attempts < 1:
            max_redis_init_attempts = 1

        dev_opt = kwargs.get('type', 'prod')
        if dev_opt == 'dev':
            self._db_num = 5
            self._reset_keys = True
        elif dev_opt == 'local':
            self._db_num = 4
            self._reset_keys = False
        else:
            self._db_num = 0
            self._reset_keys = False

        self._redis = self._init_redis_client(host=redis_host, port=redis_port, passwd=redis_pass,
                                              max_attempts=max_redis_init_attempts, db_num=self._db_num)
        if self._redis is None:
            raise RuntimeError("Unable to connect to redis database")

        # Now just get a default KeyNameHelper
        self.keynamehelper = KeyNameHelper.get_default_instance()

        if self._reset_keys:
            self._clean_keys()

    def _clean_keys(self, prefix=None):
        """
        Remove keys with a given prefix. Stop if the default prefix would result in
        removing all keys. This is used by the various use cases to clean up there
        tets data before running again.
        """
        key_prefix = prefix if prefix is not None else self.keynamehelper.prefix
        count = 0
        if key_prefix is not None:
            count = 0
            for k in self.redis.scan_iter(key_prefix + "*"):
                self.redis.delete(k)
                count += 1
        else:
            print("No prefix, no way am I going to remove '*' !")
        return count

    def create_derived_key(self, base_key: str, *args):
        return self.keynamehelper.create_derived_key(base_key, *args)

    def create_key_name(self, *args):
        return self.keynamehelper.create_key_name(*args)

    def create_field_name(self, *args):
        return self.keynamehelper.create_field_name(*args)

    @property
    def redis(self) -> Redis:
        """
        The ::class:`Redis` object for the created Redis connection.

        Returns
        -------
        Redis
            The ::class:`Redis` object for the created Redis connection.
        """
        return self._redis
