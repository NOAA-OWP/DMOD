import datetime
import heapq
import re
from abc import ABC, abstractmethod
from pathlib import Path
from docker.models.services import Service
from docker.errors import NotFound
from docker.types import SecretReference
from typing import Optional, Set, Tuple, Union

from .docker_utils import DockerSecretsUtil

from . import RsaKeyPair


class SshKeyUtil(ABC):
    """
    Abstraction for an object for providing a number of SSH keys for exclusive use.
    """

    @abstractmethod
    def acquire_ssh_rsa_key(self) -> RsaKeyPair:
        """
        Retrieve, register, and return a previously not-in-use RSA key pair, either from the reuse pool or from being
        newly generated.

        Returns
        -------
        RsaKeyPair
            A previously not-in-use RSA key pair, registered as in-use immediately before being returned
        """
        pass

    @abstractmethod
    def get_existing_keys(self) -> Set[RsaKeyPair]:
        """
        Return all known and managed key pairs for this instance, including all those currently acquired and all those
        in the reuse pool.

        Returns
        -------
        Set[RsaKeyPair]
            The set of all managed ::class:`RsaKeyPair` objects
        """
        pass

    @abstractmethod
    def get_registered_keys(self) -> Set[RsaKeyPair]:
        """
        Return the set of all registered key pairs.

        Return the set of all registered RsaKeyPair objects; i.e., those known to be currently in use.

        Returns
        -------
        Set[RsaKeyPair]
            All currently registered key pairs
        """
        pass

    @property
    @abstractmethod
    def max_reuse(self):
        pass

    @abstractmethod
    def register_ssh_rsa_key(self, key_pair: RsaKeyPair, prior_usages: int = 0):
        """
        Manually register an existing key pair as being in-use, also optionally setting the number of prior usages.

        Previously registered key pairs will result in no action being performed.

        Out-of-range ``prior_usage`` values will be replaced with 0.

        Parameters
        ----------
        key_pair
        prior_usages
        """
        pass

    @abstractmethod
    def release_ssh_rsa_key(self, key_pair: RsaKeyPair):
        """
        Release a registered RSA key pair once it is no longer needed for exclusive use, either making it available for
        reuse or retiring the key.

        Parameters
        ----------
        key_pair : RsaKeyPair
            A key pair that is no longer needed for exclusive use
        """
        pass

    @property
    @abstractmethod
    def ssh_keys_directory(self) -> Path:
        """
        Get the path to the directory containing the registered SSH keys' backing files on the file system.

        Returns
        -------
        Path
            The path to the directory containing the registered SSH keys' backing files on the file system.
        """
        pass


class SshKeyUtilImpl(SshKeyUtil):
    """
    An object for providing a number of SSH keys for exclusive use.
    """

    def __init__(self, ssh_keys_directory: Path, reusable_pool_size: int = 0, max_reuse: int = 10):
        """
        Initialize an object.

        The ``ssh_keys_directory`` argument will be used to set the ::attribute:`_ssh_keys_directory` attribute, except
        if there is an existing, non-directory file already at that path.  In these cases, the parent directory of such
        a file will be used.

        In cases when the directory at ::attribute:`_ssh_keys_directory` does not exist, it will be created.

        Reuse pool size and max reuse count are limited to the interval [0, 25].  When the argument for setting such an
        attribute is outside the valid range, the attribute will be set to the closest in-range value.

        By default, ``reusable_pool_size`` is set to 0, which results in reuse being disabled.  The default for
        ``max_reuse`` is 10.

        Parameters
        ----------
        ssh_keys_directory : Path
            A path to a working directory where actual key files will be maintained.

        reusable_pool_size : int
            The maximum number - in the interval [0, 25] - of previously acquired key pair objects to keep in a pool
            after being released to be reused.

        max_reuse : int
            The maximum number of times - in the interval [0, 25] - a released key pair object may be placed in the
            reuse pool.
        """
        if ssh_keys_directory.exists():
            self._ssh_keys_directory = ssh_keys_directory if ssh_keys_directory.is_dir() else ssh_keys_directory.parent
        else:
            self._ssh_keys_directory = ssh_keys_directory
            self._ssh_keys_directory.mkdir()

        self._pool_size = 0 if reusable_pool_size < 1 else (25 if reusable_pool_size > 25 else reusable_pool_size)
        self._max_reuse = 0 if max_reuse < 1 else (25 if max_reuse > 25 else max_reuse)

        # TODO: search directory for existing keys and either retire or make available for use

        # A dictionary of currently acquired key pair objects to prior usage counts (i.e., on first use, this is 0)
        self._registered_keys_usage_counts = dict()

        # A heap of tuples: (usage count, key pair object)
        self._reuse_pool = []

    def acquire_ssh_rsa_key(self) -> RsaKeyPair:
        """
        Retrieve, register, and return a previously not-in-use RSA key pair, either from the reuse pool or from being
        newly generated.

        Returns
        -------
        RsaKeyPair
            A previously not-in-use RSA key pair, registered as in-use immediately before being returned
        """
        if len(self._reuse_pool) > 0:
            usages, key_pair = heapq.heappop()
        else:
            timestamp_based_name = '{}_id_rsa'.format(str(datetime.datetime.now().timestamp()))
            key_pair = RsaKeyPair(directory=self._ssh_keys_directory, name=timestamp_based_name)
            usages = 0
        self._registered_keys_usage_counts[key_pair] = usages
        return key_pair

    def get_existing_keys(self) -> Set[RsaKeyPair]:
        """
        Return all known and managed key pairs for this instance, including all those currently acquired and all those
        in the reuse pool.

        Returns
        -------
        Set[RsaKeyPair]
            The set of all managed ::class:`RsaKeyPair` objects
        """
        key_pairs = set(self.get_registered_keys())
        for t in self._reuse_pool:
            key_pairs.add(t[1])
        return key_pairs

    def get_registered_keys(self) -> Set[RsaKeyPair]:
        """
        Return the set of all registered key pairs.

        Return the set of all registered RsaKeyPair objects; i.e., those known to be currently in use.

        Returns
        -------
        Set[RsaKeyPair]
            All currently registered key pairs
        """
        key_pairs = set(self._registered_keys_usage_counts.keys())
        return key_pairs

    @property
    def max_reuse(self):
        return self._max_reuse

    def register_ssh_rsa_key(self, key_pair: RsaKeyPair, prior_usages: int = 0):
        """
        Manually register an existing key pair as being in-use, also optionally setting the number of prior usages.

        Previously registered key pairs will result in no action being performed.

        Out-of-range ``prior_usage`` values will be replaced with 0.

        Parameters
        ----------
        key_pair
        prior_usages
        """
        if key_pair not in self._registered_keys_usage_counts:
            self._registered_keys_usage_counts[key_pair] = prior_usages if 0 <= prior_usages <= self._max_reuse else 0

    def release_ssh_rsa_key(self, key_pair: RsaKeyPair):
        """
        Release a registered RSA key pair once it is no longer needed for exclusive use, either making it available for
        reuse or retiring the key.

        Parameters
        ----------
        key_pair : RsaKeyPair
            A key pair that is no longer needed for exclusive use
        """
        if key_pair is None:
            # TODO: consider doing something else here
            return
        if key_pair not in self._registered_keys_usage_counts:
            raise RuntimeError("Unexpected key pair released with private key file: {}".format(
                str(key_pair.private_key_file)))

        # Get prior usage and increment by one for this time
        usage = self._registered_keys_usage_counts.pop(key_pair) + 1

        # If pool is full or this key has been reused to the max, just clean it up
        if usage >= self._max_reuse or len(self._reuse_pool) >= self._pool_size:
            key_pair.delete_key_files()
        # Otherwise, add to heap
        else:
            heapq.heappush(self._reuse_pool, (usage, key_pair))

    @property
    def ssh_keys_directory(self) -> Path:
        return self._ssh_keys_directory


class DecoratingSshKeyUtil(SshKeyUtil, ABC):
    """
    Extension of ::class:`SshKeyUtil` that decorates an inner, nested instance, received during instantiation.

    Implementations of the abstract methods in ::class:`SshKeyUtil` are all basically "pass-through."  Each method
    simply performs a call to the same method of the nested ::class:`SshKeyUtil` attribute, passing through the same
    arguments, and (when applicable) returning the result.
    """

    def __init__(self, ssh_key_util: SshKeyUtil):
        self._ssh_key_util = ssh_key_util

    def acquire_ssh_rsa_key(self) -> RsaKeyPair:
        """
        Retrieve, register, and return a previously not-in-use RSA key pair, either from the reuse pool or from being
        newly generated.

        Returns
        -------
        RsaKeyPair
            A previously not-in-use RSA key pair, registered as in-use immediately before being returned
        """
        return self._ssh_key_util.acquire_ssh_rsa_key()

    def get_existing_keys(self) -> Set[RsaKeyPair]:
        """
        Return all known and managed key pairs for this instance, including all those currently acquired and all those
        in the reuse pool.

        Returns
        -------
        Set[RsaKeyPair]
            The set of all managed ::class:`RsaKeyPair` objects
        """
        return self._ssh_key_util.get_existing_keys()

    def get_registered_keys(self) -> Set[RsaKeyPair]:
        """
        Return the set of all registered key pairs.

        Return the set of all registered RsaKeyPair objects; i.e., those known to be currently in use.

        Returns
        -------
        Set[RsaKeyPair]
            All currently registered key pairs
        """
        return self._ssh_key_util.get_registered_keys()

    @property
    def max_reuse(self):
        return self._ssh_key_util.max_reuse

    def register_ssh_rsa_key(self, key_pair: RsaKeyPair, prior_usages: int = 0):
        """
        Manually register an existing key pair as being in-use, also optionally setting the number of prior usages.

        Previously registered key pairs will result in no action being performed.

        Out-of-range ``prior_usage`` values will be replaced with 0.

        Parameters
        ----------
        key_pair
        prior_usages
        """
        self._ssh_key_util.register_ssh_rsa_key(key_pair=key_pair, prior_usages=prior_usages)

    def release_ssh_rsa_key(self, key_pair: RsaKeyPair):
        """
        Release a registered RSA key pair once it is no longer needed for exclusive use, either making it available for
        reuse or retiring the key.

        Parameters
        ----------
        key_pair : RsaKeyPair
            A key pair that is no longer needed for exclusive use
        """
        self._ssh_key_util.release_ssh_rsa_key(key_pair=key_pair)

    @property
    def ssh_keys_directory(self) -> Path:
        return self._ssh_key_util.ssh_keys_directory


class SshKeyDockerSecretsUtil(DecoratingSshKeyUtil, DockerSecretsUtil):
    """
    An extension (actually a decorator) of ::class:`SshKeyUtil` with additional functionality from the
    ::class:`DockerSecretsUtil` interface for creating and managing Docker secrets for the managed SSH keys.

    This implementation of ::class:`SshKeyUtil` assumes that key pairs registered by this instance will all be created
    having names equal to an associated Docker service id of the service that will use the keys.  This invariant can
    be maintained by only using the ::method:`init_key_pair_and_secrets_for_service` to register key pairs.

    Additionally, to ensure no keys are reused, the prior usages of keys registered using
    ::method:`init_key_pair_and_secrets_for_service` will always be set to the max number allowed by the nested
    ::class:`SshKeyUtil` instance.  This ensures they are always retired when released.
    """

    @classmethod
    def get_key_pair_secret_names(cls, key_pair: RsaKeyPair) -> Tuple[str, str]:
        """
        Get, as a tuple of strings, the appropriate names for Docker secrets corresponding to the the private and public
        keys respectively of the provided ::class:`RsaKeyPair`.

        Parameters
        ----------
        key_pair : RsaKeyPair
            A key pair for which the standardized names for Docker secrets (for the private and public keys) are wanted.

        Returns
        -------
        Tuple[str, str]
            The appropriate names for the secret for the private and public keys respectively, as a tuple of two strings
        """
        return '{}{}'.format(cls.get_private_key_secret_name_prefix(), key_pair.name), \
               '{}{}'.format(cls.get_public_key_secret_name_prefix(), key_pair.name)

    @classmethod
    def get_private_key_secret_name_prefix(cls) -> str:
        """
        Get the standard prefix to use for the names of Docker secrets for ::class:`RsaKeyPair` private keys.

        Returns
        -------
        str
            the standard prefix to use for the names of Docker secrets for ::class:`RsaKeyPair` private keys
        """
        return 'ssh_priv_key_'

    @classmethod
    def get_public_key_secret_name_prefix(cls) -> str:
        """
        Get the standard prefix to use for the names of Docker secrets for ::class:`RsaKeyPair` public keys.

        Returns
        -------
        str
            the standard prefix to use for the names of Docker secrets for ::class:`RsaKeyPair` public keys
        """
        return 'ssh_pub_key_'

    def __init__(self, ssh_key_util: SshKeyUtil, docker_client):
        super(DecoratingSshKeyUtil).__init__(ssh_key_util=ssh_key_util)
        super(DockerSecretsUtil).__init__(docker_client=docker_client)

    def _get_key_pair_for_referenced_secret(self, ref_for_secrets: Union[str, SecretReference]) -> RsaKeyPair:
        """
        Return the associated, registered ::class:`RsaKeyPair` object for a Docker secret represented by the given
        implicit reference.

        Return the associated ::class:`RsaKeyPair` object for the Docker secret represented implicitly by the supplied
        argument, where the argument can be either the name of the key pair for the secret, the name of the secret, or
        the secret's ::class:`SecretReference` object.

        If a string is passed in ``ref_for_secrets``, then its format is checked to determine whether it is a secret
        name.  If it matches the pattern of a secret name, the key pair name substring is parsed out.  If it does not,
        the string is assumed to itself be a key pair name.  Whether based on the entire string or the substring, the
        key pair name string is used to obtain the actual registered ::class:`RsaKeyPair` from the results of
        ::method:`get_registered_keys`.

        If a ::class:`SecretReference` is used, then its name is used as an argument in a recursive call to this method,
        the result returned.

        Parameters
        ----------
        ref_for_secrets : Union[str, SecretReference]
            Either the name of a key pair, the name of a key's secret, or a secret reference object for a key secret.

        Returns
        -------
        RsaKeyPair
            The associated key pair object.

        Raises
        -------
        ValueError
            If the value of ``ref_for_secrets`` cannot be used to find an associated, currently-registered
            ::class:`RsaKeyPair` object.

        """
        if isinstance(ref_for_secrets, SecretReference):
            return self._get_key_pair_for_referenced_secret(ref_for_secrets['SecretName'])
        else:
            priv_pattern = re.compile(self.get_private_key_secret_name_prefix() + '(.*)')
            priv_match = priv_pattern.match(ref_for_secrets)
            pub_pattern = re.compile(self.get_private_key_secret_name_prefix() + '(.*)')
            pub_match = pub_pattern.match(ref_for_secrets)

            if priv_match is not None:
                key_pair_name = priv_match.group(1)
            elif pub_match is not None:
                key_pair_name = pub_match.group(1)
            else:
                key_pair_name = ref_for_secrets

            kp = self._get_registered_key_pair_by_name(key_pair_name)
            if kp is not None:
                return kp

        raise ValueError("Unrecognized name for SSH key pair or associated Docker Secret used to look up key pair "
                         "object ({})".format(key_pair_name))

    def _get_registered_key_pair_by_name(self, name: str) -> Optional[RsaKeyPair]:
        """
        Get the registered key pair with the given name, or ``None`` if there is none.

        Parameters
        ----------
        name : str

        Returns
        -------
        Optional[RsaKeyPair]
            The registered key pair with the given name, or ``None`` if there is none.
        """
        for kp in self.get_registered_keys():
            if kp.name == name:
                return kp
        return None

    def _lookup_secret_by_name(self, name: str) -> Optional[SecretReference]:
        """
        Look up and return the ::class:`SecretReference` object for the Docker secret having the given name, or
        return ``None`` if no such secret can be found.

        Parameters
        ----------
        name : str
            The name of the Docker secret of interest.

        Returns
        -------
        Optional[SecretReference]
            The ::class:`SecretReference` object for the desired Docker secret, or ``None`` if none is found.
        """
        try:
            return self.docker_client.secrets.get(name, )
        except NotFound:
            return None

    def acquire_ssh_rsa_key(self) -> RsaKeyPair:
        """
        An override of the super-method, which should not be call directly for this implementation, and thus results in
        a raised ::class:`RuntimeError`.

        Raises
        -------
        RuntimeError
        """
        raise RuntimeError('Method {} cannot be executed directly by {}; use {} instead'.format(
            'acquire_ssh_rsa_key()',
            self.__class__.__name__,
            'init_key_pair_and_secrets_for_service(Service)'))

    def get_key_pair_for_service(self, service: Service) -> Optional[RsaKeyPair]:
        """
        Helper method to easily get the registered ::class:`RsaKeyPair` object associated with the given Docker service,
        or ``None`` if there is no such registered key pair.

        Parameters
        ----------
        service : Service
            The related Docker service.

        Returns
        -------
        Optional[RsaKeyPair]
            The registered ::class:`RsaKeyPair` object associated with the Docker service, or ``None`` if there is none.
        """
        return self._get_registered_key_pair_by_name(service.name)

    def init_key_pair_and_secrets_for_service(self, service: Service):
        """
        Create a dedicated ::class:`RsaKeyPair` for use by this service, register the key pair, create Docker secrets
        for the private and public keys, and attach the secrets to the service.

        Additionally, to ensure no keys are reused, the prior usages of keys is set when registering, to the max number
        allowed by the nested ::attribute:`_ssh_key_util`.  This ensures keys are always retired when released.

        Parameters
        ----------
        service : Service
            A Docker service.
        """
        key_pair = RsaKeyPair(directory=self.ssh_keys_directory, name=service.id)
        self._ssh_key_util.register_ssh_rsa_key(key_pair=key_pair, prior_usages=self._ssh_key_util.max_reuse)

        priv_key_secret_name, pub_key_secret_name = self.get_key_pair_secret_names(key_pair)
        private_key_secret_ref = self.create_docker_secret(name=priv_key_secret_name, data=key_pair.private_key_pem)
        public_key_secret_ref = self.create_docker_secret(name=pub_key_secret_name, data=key_pair.public_key)
        self.add_secrets_for_service(service, private_key_secret_ref, public_key_secret_ref)

    @property
    def max_reuse(self):
        return 0

    def register_ssh_rsa_key(self, key_pair: RsaKeyPair, prior_usages: int = 0):
        """
        An override of the super-method, which should not be call directly for this implementation, and thus results in
        a raised ::class:`RuntimeError`.

        Parameters
        ----------
        key_pair
        prior_usages

        Raises
        -------
        RuntimeError
        """
        raise RuntimeError('Method {} cannot be executed directly by {}; use {} instead'.format(
            'register_ssh_rsa_key(RsaKeyPair, int)',
            self.__class__.__name__,
            'init_key_pair_and_secrets_for_service(Service)'))

    def release_all_for_stopped_services(self):
        """
        Release any still-registered key pairs for Docker services that are no longer running, cleaning up any
        associated Docker secrets as well.

        The method assumes that key pairs registered by this instance and its spawned services will all be created
        having names equal to the Docker service id of the service that will use the keys.  As such, if the service is
        no longer found, it has finished, and the key pair of the same name can be cleaned up.
        """
        for key_pair in self.get_registered_keys():
            try:
                service = self.docker_client.services.get(key_pair.name, )
            except NotFound as e:
                self.release_ssh_key_and_secrets(lookup_obj=key_pair, assume_service_removed=True)

    def release_ssh_key_and_secrets(self,
                                    lookup_obj: Union[RsaKeyPair, str, SecretReference],
                                    assume_service_removed: bool = False,
                                    should_delete: bool = True):
        """
        Release the appropriate SSH-key-related Docker secrets from use by their service (if it still exists), delete
        the secrets, and release the key pair.

        If a string or ::class:`SecretReference` is passed in ``lookup_obj``, the
        ::method:`_get_key_pair_for_referenced_secret` is used to obtain the appropriate key pair object.  Otherwise,
        the ``lookup_obj`` is expected to itself be a ::class:`RsaKeyPair` object.

        If a ::class:`RsaKeyPair` object is passed in ``lookup_obj``, then the names for the private and public key
        secrets can be derived from the name of the key pair.  Also, the service id is directly equal to the name of the
        key pair, making the service itself easy to find.

        Parameters
        ----------
        lookup_obj : Union[RsaKeyPair, str, SecretReference]
            Either the related key pair or a means of referencing it that can be used by
            ::method:`_get_key_pair_for_referenced_secret` to find the key pair.

        assume_service_removed : bool
            Whether it is safe to assume the related Docker service has already been removed, and thus it is not.

        should_delete : bool
            Whether the secret should be deleted/removed, which is ``True`` by default.
        """
        # First, ensure we have an RsaKeyPair object
        key_pair = None
        if isinstance(lookup_obj, SecretReference) or isinstance(lookup_obj, str):
            # Note that this will raise a ValueError here if it can't find a key pair object
            key_pair = self._get_key_pair_for_referenced_secret(lookup_obj)
        elif isinstance(lookup_obj, RsaKeyPair):
            key_pair = lookup_obj
        if key_pair is None:
            raise TypeError(
                "Invalid type passed to release SSH key secrets (was {})".format(lookup_obj.__class__.__name__))

        # Then obtain the secrets based on knowing the key pair
        private_key_secret_ref = self.docker_client.secrets.get(self.get_key_pair_secret_names(key_pair)[0], )
        public_key_secret_ref = self.docker_client.secrets.get(self.get_key_pair_secret_names(key_pair)[1], )

        # Determine if service still exists and, if so, remove secrets from it
        if not assume_service_removed:
            try:
                service = self.docker_client.services.get(key_pair.name, )
                self.remove_secrets_for_service(service, private_key_secret_ref, public_key_secret_ref)
            except NotFound:
                pass

        # Delete the secrets
        if should_delete:
            if private_key_secret_ref is not None:
                private_key_secret_ref.remove()
            if public_key_secret_ref is not None:
                public_key_secret_ref.remove()

        # Finally, release the key pair
        self.release_ssh_rsa_key(key_pair)
