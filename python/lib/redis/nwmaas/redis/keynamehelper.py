
#__prefix__ = ""
#__sep__ = ":"


class KeyNameHelper:
    """
    Utility class, based on original scheduler package utility function, with helper functions to generate key and field
    names based on variadic params.

    E.g., by default, given the arguments ``"foo", "bar"``, functions will generate something like ``foo:bar``.
    """

    __PREFIX__ = ""
    __SEPARATOR__ = ":"

    @classmethod
    def ensure_str(cls, vals):
        str_vals = []
        for v in vals:
            if isinstance(v,bytes):
                str_vals.append(v.decode())
            else:
                str_vals.append(v)
        return str_vals

    @classmethod
    def get_default_instance(cls) -> 'KeyNameHelper':
        """
        Get a default instance, with default prefix (``""``) and separator (``:``) values.

        Returns
        -------
        KeyNameHelper
            A default instance of this class.
        """
        return cls(prefix=cls.get_default_prefix(), separator=cls.get_default_separator())

    @classmethod
    def get_default_prefix(cls):
        return cls.__PREFIX__

    @classmethod
    def get_default_separator(cls):
        return cls.__SEPARATOR__

    def __init__(self, prefix: str, separator: str):
        self._prefix = prefix
        self._separator = separator

    def create_field_name(self, *vals):
        """Create the field name based on the following format

           [ [ separator + value] ]

        Typically used for field names in a hash, where you don't need the prefix
        added, because the returned value is used in the context of a key.
        """
        return "%s" % self.separator.join(self.ensure_str(vals))

    def create_key_name(self, *vals):
        """Create the key name based on the following format

           [ prefix + sepatartor] + [ [ separator + value] ]
        """
        start = (self.prefix + self.separator) if self.prefix != b"" else ""
        return start + "%s" % self.separator.join(self.ensure_str(vals))

    @property
    def prefix(self):
        return self._prefix

    @property
    def separator(self):
        return self._separator
