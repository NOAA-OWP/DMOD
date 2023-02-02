from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from dmod.core.serializable import Serializable
from pathlib import Path
from pydantic import Field, PrivateAttr, validator
from typing import ClassVar, Dict, Optional, Tuple, Union
from typing_extensions import Self
import datetime
import os

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKeyWithSerialization

class _RsaKeyPair(Serializable):
    """
    This is a shim object that enables partial instantiation of a :class:`RsaKeyPair`. This class exposes methods and
    properties to interact, generate, and write a key pair. However, it does not expose a way to serialize or
    deserialize keys and other associated metadata from a dictionary. For the functionality, see :class:`RsaKeyPair`.
    """

    directory: Path
    """
    The directory in which the key pair files have been or will be written, as a :class:`Path`.

    If `None` is provided, `directory` defaults to ``$HOME/.ssh/``. If the default or provided directory does not
    exists, it and any intermediate directories will be created. Directory inputs that exist and are not directories
    (i.e. a file) will raise a ValueError.
    """

    name: str = Field(min_length=1)
    """Basename of private key file."""

    _priv_key: RSAPrivateKeyWithSerialization = PrivateAttr(None)
    _priv_key_pem: bytes = PrivateAttr(None)
    _is_deserialized: bool = PrivateAttr(False)

    @validator("directory", pre=True)
    def _validate_directory(cls, value: Union[str, Path, None]) -> Union[str, Path]:
        if value is None:
            return Path.home() / ".ssh"

        if isinstance(value, str):
            return value.strip()

        return value

    @validator("directory")
    def _post_validate_directory(cls, value: Path) -> Path:
        if not value.exists():
            value.mkdir(parents=True)

        elif not value.is_dir():
            raise ValueError(f"Existing non-directory file at path provided for key pair directory. {value!r}")

        return value

    @validator("name")
    def _validate_name(cls, value: str) -> str:
        return value.strip()

    @property
    def private_key_file(self) -> Path:
        """

        Returns
        -------
        Path
            Path to private key file. Is not guaranteed to exist.
        """
        return self.directory / self.name

    @property
    def public_key_file(self) -> Path:
        """
        Same as private key filepath, but with the suffix ".pub".

        Returns
        -------
        Path
            Path to public key file. Is not guaranteed to exist.
        """
        return self.directory / f"{self.name}.pub"

    @property
    def private_key_pem(self) -> bytes:
        """

        Returns
        -------
        bytes
            Encoded private key in PEM format
        """
        if self._priv_key_pem is None:
            self._priv_key_pem = self._private_key_bytes_from_private_key(self._private_key)
        return self._priv_key_pem # type: ignore

    def delete_key_files(self) -> Tuple[bool, bool]:
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

    def write_key_files(self, write_private: bool = True, write_public: bool = True):
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
        # if fail to write private key file, delete any existing pub / priv key files.
        try:
            if write_private and not self.private_key_file.exists():
                self._write_private_key(self._private_key, raise_on_fail=True)
        except Exception as e:
            if self.public_key_file.exists():
                _, deleted_public = self.delete_key_files()
                if not deleted_public:
                    raise RuntimeError(f"Failed to write private key file. During failure, failed to remove public key file. '{self.public_key_file}'") from e
            raise e

        # NOTE: if cannot write pub key file, priv key file, if it exists, will not be removed.
        if write_public and not self.public_key_file.exists():
            self._write_public_key(self._private_key, raise_on_fail=True)

    @property
    def _private_key(self) -> RSAPrivateKeyWithSerialization:
        """
        Serialized private key. Lazily loads private key from :property:`private_key_file` or dynamically generates one.

        If the private key is loaded from :property:`private_key_file` and :property:`public_key_file` does not exist, a
        public key is written to disk at :property:`public_key_file`.
        """
        if self._priv_key is None and self.private_key_file.exists():
            priv_key_file = self.private_key_file.read_bytes()
            self._priv_key = serialization.load_pem_private_key(priv_key_file, None, default_backend())
            self._is_deserialized = True

            self._write_public_key(self._priv_key, overwrite=False, raise_on_fail=True)

        elif self._priv_key is None:
            self._priv_key = rsa.generate_private_key(backend=default_backend(), public_exponent=65537, key_size=3072)

        return self._priv_key # type: ignore

    @staticmethod
    def _public_key_bytes_from_private_key(private_key: RSAPrivateKeyWithSerialization) -> bytes:
        return private_key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)

    @staticmethod
    def _private_key_bytes_from_private_key(private_key:  RSAPrivateKeyWithSerialization) -> bytes:
        return private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                         format=serialization.PrivateFormat.TraditionalOpenSSL,
                                         encryption_algorithm=serialization.NoEncryption())

    @staticmethod
    def _read_private_key_ctime(location: Path) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(os.path.getctime(str(location)))

    @staticmethod
    def __try_write(content: str, location: Path, overwrite: bool = False, raise_on_fail: bool = False) -> bool:
        if not overwrite and location.exists():
            return False
        try:
            location.write_text(content)
        except Exception as e:
            if raise_on_fail:
                raise e
            return False
        return True

    def _write_public_key(self, private_key: RSAPrivateKeyWithSerialization, overwrite: bool = False, raise_on_fail: bool = False) -> bool:
        pub_key = self._public_key_bytes_from_private_key(private_key).decode("utf-8")
        return self.__try_write(pub_key, self.public_key_file, overwrite=overwrite, raise_on_fail=raise_on_fail)

    def _write_private_key(self, private_key: RSAPrivateKeyWithSerialization, overwrite: bool = False, raise_on_fail: bool = False) -> bool:
        priv_key = self._private_key_bytes_from_private_key(private_key).decode("utf-8")
        return self.__try_write(priv_key, self.private_key_file, overwrite=overwrite, raise_on_fail=raise_on_fail)

    def _delete_existing_key_files_if_priv_keys_differ(self):
        # Remove any existing private/public key files unless the contents match serialized private key value
        if self.private_key_file.exists():
            priv_key_file_bytes = self.private_key_file.read_bytes()

            if priv_key_file_bytes != self._private_key_bytes_from_private_key(self._private_key):
                self.public_key_file.unlink(missing_ok=True)
                self.private_key_file.unlink()
                raise RuntimeError("Existing private key from file does not match provided private.")

        elif self.public_key_file.exists():
            # Always remove an existing public key file if there was not a private key file
            self.public_key_file.unlink()


class RsaKeyPair(_RsaKeyPair, Serializable):
    """
    Representation of an RSA key pair and certain meta properties, in particular a name for the key and a pair of
    :class:`Path` objects for its private and public key files. Keys may be either dynamically generated or deserialized
    from existing files.

    Key file basenames are derived from the :attr:`name` value for the object, which is set from an init param that
    defaults to ``id_rsa`` if not provided. However, :attr:`name` is a required field when initializing from a
    dictionary. The public key file will have the same basename as the private key file, except with the ``.pub``
    extension added.

    When the private key file already exists, the private key will be deserialized from the file contents.  This will
    happen immediately when the object is created.

    When the private key file does not already exists, the actual keys will be generated dynamically -- but not written
    to a file. Use the :method:`write_key_files` to write key pairs to a file.

    Note that rich comparisons for ``==`` and ``<`` are expressly defined, with the other implementations being derived
    from these two.

    inv:
        # The basename of the private key file will always be the key pair's name
        self.name == self.private_key_file.name

    """

    private_key: RSAPrivateKeyWithSerialization
    """
    Serialized private key for this key pair object.
    """

    generation_time: datetime.datetime

    _pub_key: bytes = PrivateAttr(None)
    __private_key_text: str = PrivateAttr(None)

    _SERIAL_DATETIME_STR_FORMAT: ClassVar[str] = '%Y-%m-%d %H:%M:%S.%f'

    @validator("generation_time", pre=True)
    def _validate_datetime(cls, value: Union[str, datetime.datetime]) -> datetime.datetime:
        if isinstance(value, datetime.datetime):
            return value

        return datetime.datetime.strptime(value, cls.get_datetime_str_format())

    @validator("private_key", pre=True)
    def _validate_private_key(cls, value: Union[str, RSAPrivateKeyWithSerialization ]) -> RSAPrivateKeyWithSerialization:
        if isinstance(value, RSAPrivateKeyWithSerialization):
            return value

        priv_key_bytes = value.encode("utf-8")
        return serialization.load_pem_private_key(priv_key_bytes, None, default_backend())

    class Config: # type: ignore
        arbitrary_types_allowed = True
        def _serialize_datetime(self: "RsaKeyPair", value: datetime.datetime) -> str:
            return value.strftime(self.get_datetime_str_format())

        field_serializers = {
            "generation_time": _serialize_datetime,
            "private_key": lambda self, _: self._private_key_text,
            "directory": lambda directory: str(directory),
        }

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: Dict[str, str]) -> Optional[Self]:
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        The format should be as follows:

            {
                'name': 'name_value',
                'directory': 'directory_path_as_string',
                'private_key': 'private_key_text',
                'generation_time': 'generation_time_str'
            }

        Parameters
        ----------
        json_obj : dict
            A serialized representation of an instance, in the form of a JSON dictionary object.

        Returns
        -------
        Optional[RsaKeyPair]
            A new key pair object instantiated from the deserialize JSON object dictionary, or ``None`` if the provided
            JSON object is not valid for creating a new instance.
        """
        err_msg_start = 'Cannot deserialize {} object'.format(cls.__name__)
        try:
            # Sanity check serialized structure
            for field in cls.__fields__.values():
                if field.alias not in json_obj:
                    raise RuntimeError('{}: missing required serial {} key'.format(err_msg_start, field.alias))

            o = cls(**json_obj)
            o._is_deserialized = True
            return o
        except:
            # TODO: log error
            return None

    def __eq__(self, other: Self) -> bool:
        return other is not None \
               and self.generation_time == other.generation_time \
               and self._private_key_text == other._private_key_text \
               and self.private_key_file.absolute() == other.private_key_file.absolute()

    def __ge__(self, other: Self):
        return not self < other

    def __gt__(self, other: Self):
        return not self <= other

    def __init__(self, directory: Union[str, Path, None], name: str = "id_rsa", **data):
        """
        Initialize an instance.

        Parameters
        ----------
        directory : str, Path, None
            The path (either as a :class:`Path` or string) to the parent directory for the backing key files, or
            ``None`` if the default of ``{$HOME}/.ssh/`` should be used.

        name : str
            The name to use for the key pair, which will also be the basename of the private key file and the basis of
            the basename of the public key file (``id_rsa`` by default).
        """
        # If `data` exists, we assume we are deserializing a message with all required fields.
        # NOTE: method, `factory_init_from_deserialized_json`, verifies that all fields are passed
        # before trying to initialize.
        if data:
            super().__init__(
                directory=directory,
                name=name,
                **data
            )
            # indirectly set `_private_key` property of parent class `_RsaKeyPair`.
            # as a result a public key file will not be created during initialization even if a
            # private key file exists and its contents match the passed `private_key` field and a
            # public key file does not exist.
            self._priv_key = self.private_key
            self._delete_existing_key_files_if_priv_keys_differ()

        # If `data` does not exists, partially initialize using fields we have, then derive / create
        # all required byt unspecified fields. Then, fully initialize.
        else:
            key_pair = _RsaKeyPair(directory=directory, name=name)
            # lazily generate or load private key
            private_key = key_pair._private_key
            # could raise `RuntimeError`
            key_pair._delete_existing_key_files_if_priv_keys_differ()
            key_pair.write_key_files()
            generation_time = key_pair._read_private_key_ctime(key_pair.private_key_file)

            super().__init__(
                directory=directory,
                name=name,
                private_key=private_key,
                generation_time=generation_time,
            )

            # transfer how the key pair was created
            self._is_deserialized = key_pair._is_deserialized
            # no one should access this directly nor through property, `_private_key`, but just in case.
            self._priv_key = self.private_key

    def __hash__(self) -> int:
        hash_str = '{}:{}:{}'.format(self._private_key_text,
                                     str(self.private_key_file.absolute()),
                                     self.generation_time.strftime(self.get_datetime_str_format()))
        return hash(hash_str)

    def __le__(self, other: Self) -> bool:
        return self == other or self < other

    def __lt__(self, other: Self) -> bool:
        if self.generation_time != other.generation_time:
            return self.generation_time < other.generation_time
        elif self._private_key_text != other._private_key_text:
            return self._private_key_text < other._private_key_text
        else:
            return self.private_key_file.absolute() < other.private_key_file.absolute()

    @property
    def _private_key_text(self) -> str:
        if self.__private_key_text is None:
            self.__private_key_text = self.private_key_pem.decode("utf-8")
        return self.__private_key_text # type: ignore

    @property
    def is_deserialized(self) -> bool:
        """
        Whether this object was deserialized from an already-existing file or serialized object, as opposed to being
        created and dynamically generating its keys.

        Returns
        -------
        bool
            Whether this object was created from a pre-existing private key file
        """
        return self._is_deserialized

    @property
    def public_key(self) -> bytes:
        if self._pub_key is None:
            self._pub_key = self._public_key_bytes_from_private_key(self.private_key)
        return self._pub_key

    def write_key_files(self, write_private: bool = True, write_public: bool = True):
        super().write_key_files(write_private=write_private, write_public=write_public)
        if write_private:
            # update generation time
            self.generation_time = self._read_private_key_ctime(self.private_key_file)
