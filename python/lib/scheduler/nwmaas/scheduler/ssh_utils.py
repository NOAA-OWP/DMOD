from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from pathlib import Path
from typing import Union

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKeyWithSerialization


class RsaKeyPair:
    """
    Representation of an RSA key pair with a given name and pair of paths where key files can be or have been written.

    File basenames are derived from the :attr:`name` value for the object, which is set from an init param which
    defaults to ``id_rsa`` if not provided.  The public key file will have the same basename as the private key file,
    except with the ``.pub`` extension added.

    When the private key file already exists, the private key will be deserialized from the file contents.  This will
    happen immediately when the object is created.

    When the private key file does not already exists, the actual keys will be generated dynamically, though this is
    performed lazily.  The :method:`generate_key_pair` method will trigger all necessary lazy instantiations and also
    cause the key files to be written.
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

        if self.private_key_file.exists():
            with self.private_key_file.open('rb') as priv_key_file:
                self._priv_key = serialization.load_pem_private_key(priv_key_file.read(), None, default_backend())
                if not self.public_key_file.exists():
                    self._write_key_files(write_private=False)
                self._files_written = True
        else:
            self._files_written = False

    def __hash__(self) -> int:
        self.generate_key_pair()
        base_str = '{}:{}:{}'.format(str(self.private_key_file.absolute()), str(self.public_key_file.absolute()),
                                     self._private_key_text)
        return hash(base_str)

    def __eq__(self, other: 'RsaKeyPair') -> bool:
        return self.private_key_file.absolute() == other.private_key_file.absolute() \
               and self.public_key_file.absolute() == other.public_key_file.absolute() \
               and self._private_key_text == other._private_key_text

    def _load_key_text(self):
        if self._private_key_text is None:
            self._private_key_text = self.private_key_pem.decode('utf-8')
        if self._public_key_text is None:
            self._public_key_text = self.public_key.decode('utf-8')

    def _write_key_files(self, load_key_text=True, write_private=True, write_public=True):
        if load_key_text:
            self._load_key_text()
        if write_private:
            self.private_key_file.write_text(self._private_key_text)
        if write_public:
            self.public_key_file.write_text(self._public_key_text)

    def generate_key_pair(self):
        if not self._files_written:
            # Works via a lot of lazy instantiation
            self._write_key_files()

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
    def name(self):
        return self._name

    @property
    def private_key(self) -> RSAPrivateKeyWithSerialization:
        if self._priv_key is None:
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

