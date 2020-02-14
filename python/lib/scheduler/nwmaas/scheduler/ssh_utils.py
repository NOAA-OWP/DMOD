from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from pathlib import Path
from typing import Union
import datetime
import os

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKeyWithSerialization


class RsaKeyPair:
    """
    Representation of an RSA key pair and certain meta properties, in particular a name for the key and a pair of
    :class:`Path` objects for its private and public key files. Keys may be either dynamically generated or deserialized
    from existing files.

    Key file basenames are derived from the :attr:`name` value for the object, which is set from an init param that
    defaults to ``id_rsa`` if not provided.  The public key file will have the same basename as the private key file,
    except with the ``.pub`` extension added.

    When the private key file already exists, the private key will be deserialized from the file contents.  This will
    happen immediately when the object is created.

    When the private key file does not already exists, the actual keys will be generated dynamically, though this is
    performed lazily.  The :method:`generate_key_pair` method will trigger all necessary lazy instantiations and also
    cause the key files to be written.

    Note that rich comparisons for ``==`` and ``<`` are expressly defined, with the other implementations being derived
    from these two.

    inv:
        # The basename of the private key file will always be the key pair's name
        self.name == self.private_key_file.name

        # The returned generation time property value will always be equal to the time stamp of the private key file
        self.generation_time == datetime.datetime.fromtimestamp(os.path.getctime(str(self.private_key_file)))

    """

    def __init__(self, directory: Union[str, Path, None], name: str = 'id_rsa'):
        self._name = name.strip()
        if self._name is None or len(self._name) < 1:
            raise ValueError("Invalid key pair name")

        self.directory = directory

        self._public_key_file = None
        self._private_key_file = None

        self._priv_key = None
        self._priv_key_pem = None
        self._pub_key = None

        self._private_key_text = None
        self._public_key_text = None

        self._is_deserialized = None
        self._generation_time = None
        self._files_written = False

    def __hash__(self) -> int:
        hash_str = '{}:{}:{}'.format(self._get_private_key_text(),
                                     str(self.private_key_file.absolute()),
                                     self.generation_time.strftime('%Y-%m-%d,%H:%M:%S.%f'))
        return hash_str.__hash__()

    def __eq__(self, other: 'RsaKeyPair') -> bool:
        return self.generation_time == other.generation_time \
               and self._get_private_key_text() == other._get_private_key_text() \
               and self.private_key_file.absolute() == other.private_key_file.absolute()

    def __ge__(self, other):
        return not self < other

    def __gt__(self, other):
        return not self <= other

    def __le__(self, other: 'RsaKeyPair') -> bool:
        return self == other or self < other

    def __lt__(self, other: 'RsaKeyPair') -> bool:
        if self.generation_time != other.generation_time:
            return self.generation_time < other.generation_time
        elif self._get_private_key_text != other._get_private_key_text:
            return self._get_private_key_text < other._get_private_key_text
        else:
            return self.private_key_file.absolute() < other.private_key_file.absolute()

    def _get_private_key_text(self):
        if self._private_key_text is None:
            self._load_key_text()
        return self._private_key_text

    def _load_key_text(self):
        if self._private_key_text is None:
            self._private_key_text = self.private_key_pem.decode('utf-8')
        if self._public_key_text is None:
            self._public_key_text = self.public_key.decode('utf-8')

    def _read_private_key_ctime(self, skip_file_exists_check=False):
        if skip_file_exists_check or self.private_key_file.exists():
            return datetime.datetime.fromtimestamp(os.path.getctime(str(self.private_key_file)))
        else:
            return None

    def write_key_files(self, write_private=True, write_public=True):
        """
        Write private and/or public keys to files at :attr:`private_key_file` and :attr:`public_key_file` respectively,
        assuming the respective file does not already exist.

        Parameters
        ----------
        write_private : bool
            An option, ``True`` by default, for whether the private key should be written to :attr:`private_key_file`

        write_public : bool
            An option, ``True`` by default, for whether the public key should be written to :attr:`public_key_file`
        """
        self._load_key_text()
        if write_private and not self.private_key_file.exists():
            self.private_key_file.write_text(self._get_private_key_text())
            self._is_deserialized = False
        if write_public and not self.public_key_file.exists():
            self.public_key_file.write_text(self._public_key_text)

    def delete_key_files(self) -> tuple:
        """
        Delete the files at the paths specified by :attr:`private_key_file` and :attr:`public_key_file`, as long as
        there is an existing, regular (i.e., from :method:`Path.is_file`) file at the individual paths.

        Note that whether a delete is performed for one file is independent of what the state of the other.  I.e., if
        the private key file does not exist, thus resulting in no attempt to delete it, this will not affect whether
        there is a delete operation on the public key file.

        Returns
        -------
        tuple
            A tuple of boolean values, representing whether the private key file and the public key file respectively
            were deleted
        """
        deleted_private = False
        deleted_public = False
        if self.private_key_file.exists() and self.private_key_file.is_file():
            self.private_key_file.unlink()
            deleted_private = True
        if self.public_key_file.exists() and self.public_key_file.is_file():
            self.public_key_file.unlink()
            deleted_public = True
        return deleted_private, deleted_public

    @property
    def generation_time(self):
        if self._generation_time is None:
            if not self.private_key_file.exists():
                self.write_key_files()
            self._generation_time = self._read_private_key_ctime(skip_file_exists_check=True)
        return self._generation_time

    @property
    def directory(self) -> Path:
        """
        Get the directory in which the key pair files have been or will be written, as a :class:`Path`, lazily
        instantiating if needed (using the property setter) to ``.ssh/`` within the home directory of the user.

        Returns
        -------
        Path
            The directory in which the key pair files have been or will be written
        """
        if self._directory is None:
            self.directory = Path.home().joinpath(".ssh")
        return self._directory

    @directory.setter
    def directory(self, d: Union[str, Path, None]):
        """
        Set the directory in which the key pair files have been or will be written, creating the actual directory in the
        filesystem if given a valid, non-existing path.

        Parameters
        ----------
        d : str, Path, or None
            A representation of the value to set for the directory, either as a str or :class:`Path`, or simply ``None``
        """
        # Make sure we are working with either None or the equivalent Path object for a path as a string
        d_path = Path(d) if isinstance(d, str) else d
        if d_path is not None:
            if not d_path.exists():
                d_path.mkdir()
            elif not d_path.is_dir():
                raise ValueError("Existing non-directory file at path provided for key pair directory")
        self._directory = d_path

    @property
    def is_deserialized(self) -> bool:
        """
        Whether this object was deserialized from an already-existing file, as opposed to being created and dynamically
        generating its keys.

        pre: self._is_deserialized is not None or self._priv_key is None

        post: self._is_deserialized is not None and self._priv_key is not None

        Returns
        -------
        bool
            Whether this object was created from a pre-existing private key file
        """
        if self._is_deserialized is None:
            # We don't actually need the value directly, but the lazy instantiation will set _is_deserialized as a side-
            # effect, since it intrinsically has to determine whether it can/should deserialized the private key
            priv_key = self.private_key
        return self._is_deserialized

    @property
    def name(self):
        return self._name

    @property
    def private_key(self) -> RSAPrivateKeyWithSerialization:
        """
        Get the private key for this key pair object, lazily instantiating if necessary either through deserialization
        or by dynamically generating a key.

        Note that, since lazy instantiation requires determining if the value should be deserialized, the attribute
        backing the :attr:`is_deserialized` property is set as a side effect when performing that step.

        post: self._is_deserialized is not None

        Returns
        -------
        RSAPrivateKeyWithSerialization
            The actual RSA private key object
        """
        if self._priv_key is None and self.private_key_file.exists():
            with self.private_key_file.open('rb') as priv_key_file:
                self._priv_key = serialization.load_pem_private_key(priv_key_file.read(), None, default_backend())
                if not self.public_key_file.exists():
                    self.write_key_files(write_private=False)
                self._files_written = True
                self._is_deserialized = True
        elif self._priv_key is None:
            self._priv_key = rsa.generate_private_key(backend=default_backend(), public_exponent=65537, key_size=3072)
        return self._priv_key

    @property
    def private_key_file(self) -> Path:
        """
        Get the path to the private key file, lazily instantiating using the :attr:`name` and :method:`directory`.

        Returns
        -------
        Path
            The path to the private key file
        """
        if self._private_key_file is None:
            self._private_key_file = None if self.directory is None else self.directory.joinpath(self._name)
        return self._private_key_file

    @property
    def private_key_pem(self):
        if self._priv_key_pem is None:
            self._priv_key_pem = self.private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                                                format=serialization.PrivateFormat.TraditionalOpenSSL,
                                                                encryption_algorithm=serialization.NoEncryption())
        return self._priv_key_pem

    @property
    def public_key(self):
        if self._pub_key is None:
            self._pub_key = self.private_key.public_key().public_bytes(serialization.Encoding.OpenSSH,
                                                                       serialization.PublicFormat.OpenSSH)
        return self._pub_key

    @property
    def public_key_file(self) -> Path:
        """
        Get the path to the public key file, lazily instantiating based on the :attr:`name` and :method:`directory`.

        Returns
        -------
        Path
            The path to the public key file
        """
        if self._public_key_file is None:
            self._public_key_file = None if self.directory is None else self.directory.joinpath(self._name + '.pub')
        return self._public_key_file
