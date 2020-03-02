import datetime
import heapq
from pathlib import Path

from nwmaas.scheduler.rsa_key_pair import RsaKeyPair


class SshKeyUtil:
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

        Pool and reuse amounts are limited to the interval [0, 25].  When the argument for setting such an attribute is
        outside the valid range, the attribute will be set to the closest in-range value.

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
        self._acquired_keys_usage_counts = dict()

        # A heap of tuples: (usage count, key pair object)
        self._reuse_pool = []

    def acquire_ssh_rsa_key(self) -> RsaKeyPair:
        """
        Request a not-in-use RSA key pair for use.

        Returns
        -------
        RsaKeyPair
            A not-in-use RSA key pair
        """
        if len(self._reuse_pool) > 0:
            usages, key_pair = heapq.heappop()
        else:
            timestamp_based_name = '{}_id_rsa'.format(str(datetime.datetime.now().timestamp()))
            key_pair = RsaKeyPair(directory=self._ssh_keys_directory, name=timestamp_based_name)
            usages = 0
        self._acquired_keys_usage_counts[key_pair] = usages
        return key_pair

    def release_ssh_rsa_key(self, key_pair: RsaKeyPair):
        """
        Release a previously-acquired RSA key pair once it is no longer needed for exclusive use, either making it
        available for reuse or retiring the key.

        Parameters
        ----------
        key_pair : RsaKeyPair
            A key pair that is no longer needed for exclusive use
        """
        if key_pair is None:
            # TODO: consider doing something else here
            return
        if key_pair not in self._acquired_keys_usage_counts:
            raise RuntimeError("Unexpected key pair released with private key file: {}".format(
                str(key_pair.private_key_file)))

        # Get prior usage and increment by one for this time
        usage = self._acquired_keys_usage_counts.pop(key_pair) + 1

        # If pool is full or this key has been reused to the max, just clean it up
        if usage >= self._max_reuse or len(self._reuse_pool) >= self._pool_size:
            key_pair.delete_key_files()
        # Otherwise, add to heap
        else:
            heapq.heappush(self._reuse_pool, (usage, key_pair))
