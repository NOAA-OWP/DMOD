import datetime
import heapq
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Set

from nwmaas.scheduler.rsa_key_pair import RsaKeyPair


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


