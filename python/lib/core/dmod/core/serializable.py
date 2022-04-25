from abc import ABC, abstractmethod
from numbers import Number
from typing import Callable, Dict, Type, Union
import json


class Serializable(ABC):
    """
    An interface class for an object that can be serialized to a dictionary-like format (i.e., potentially a JSON
    object) and JSON string format based directly from dumping the aforementioned dictionary-like representation.

    Objects of this type will also used the JSON string format as their default string representation.

    While not strictly enforced (because this probably isn't possible), it is HIGHLY recommended that instance
    attribute members of implemented sub-types be of types that are either convertible to strings using the ``str()``
    built-in, or are themselves also implementations of ::class:`Serializable`.  The convenience class method
    ::method:`serialize` will handle serializing any such member objects appropriately, providing a clean interface for
    this.

    An exception to the aforementioned recommendation is the ::class:`datetime.datetime` type.  Subtype attributes of
    ::class:`datetime.datetime` type should be parsed and serialized using the pattern returned by the
    ::method:`get_datetime_str_format` class method.  A reasonable default is provided in the base interface class, but
    the pattern can be adjusted eitehr by overriding the class method directly or by having a subtypes set/override
    its ::attribute:`_SERIAL_DATETIME_STR_FORMAT` class attribute.  Note that the actual parsing/serialization logic is
    left entirely to the subtypes, as many will not need it (and thus should not have to worry about implement another
    method or have their superclass bloated by importing the ``datetime`` package).
    """

    _SERIAL_DATETIME_STR_FORMAT = '%Y-%m-%d %H:%M:%S'

    @classmethod
    def _get_invalid_type_message(cls):
        invalid_type_msg = 'Invalid deserialized type for ' + cls.__name__ + ' property {}: expected {} but got {}'
        return invalid_type_msg

    @classmethod
    @abstractmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        A new object of this type instantiated from the deserialize JSON object dictionary
        """
        pass

    @classmethod
    def get_datetime_str_format(cls):
        """
        Get the string representation of the datetime format pattern for serializing date and time objects used by this
        class.

        Returns
        -------
        str
            The string representation of the datetime format pattern for serializing date and time objects used by this
            class.
        """

        return cls._SERIAL_DATETIME_STR_FORMAT

    @classmethod
    def parse_simple_serialized(cls, json_obj: dict, key: str, expected_type: Type, required_present: bool = True,
                                converter: Callable = None):
        """
        Parse a value of a specified type out of a dictionary, possibly converting a present value to an equivalent of
        the expected type, and throw errors if a value of the expected type cannot be obtained.

        This method attempts to retrieve a value from the provided dictionary at the specified key.  If the given lookup
        key is not present in the dictionary, and thus no value can be retrieved, either ``None`` is returned or a
        ::class:`RuntimeError` is raised.  This depends on whether it is required the value be present, as controlled by
        the ``required_present`` param (which is ``True`` by default).

        If a value can be retrieved from the dictionary, it must be of the provided expected type.  A
        ::class:`RuntimeError` is raised if the method cannot (eventually) obtain a value of the expected type.  If a
        value of the expected type is either retrieved directly or obtained via conversion (without information loss),
        it is returned.

        A converter callable may optionally be passed to try to convert an "original" value of a different type to the
        expected type if necessary.  E.g., it is sensible when expecting a numeric value be able to handle getting a
        string representation like ``"5"``, so a function can be passed that accounts for this and converts the value.
        Note that errors during a conversion attempt are currently caught and obscured, with the aforementioned
        ::class:`RuntimeError` being raised after.

        Additionally, it is required that converted representations be truly equivalent, in particular for numeric
        types, which is not automatically the case after successful conversions.  As such, original and converted values
        are tested for equivalence IFF they are both some numeric type.  A ::class:`RuntimeError` is raised in such
        cases if the values are not equivalent.

        It is strongly recommended that conversion functions not process values through any intermediate types before
        returning the eventual converted value (e.g., going from string to float to int to handle an original value
        like ``"5.0"``), as this risks losing information in a way that is not possible to protect against generally
        (e.g., an original value of ``"5.1"`` would be converted to ``5.1`` and then to ``5``, but since the original
        value was non-numeric no equivalence check is performed, nor is it easy to introduce one).

        A ::class:`ValueError` is raised if a conversion takes place successfully but does not produce a converted value
        of the expected type (i.e. effectively an invalid conversion function).

        Parameters
        ----------
        json_obj: dict
            The containing serialize dictionary.
        key: str
            The key for the value of interest.
        expected_type: Type
            The expected type for the value.
        required_present: bool
            Whether the key not being present in the dictionary causes an error to be raised.
        converter: Callable
            A callable handle to potentially use to try to convert parsed values of non-expected types to expected type.

        Returns
        -------
        The parsed value of the expected type, possibly after conversion, or ``None`` the ``required`` parameter is
        ``False`` and the value's key is not present.

        Raises
        -------
        RuntimeError
            If either the value is required and not present; the value is not of the expected type and there is not
            provided conversion callable; the value is not of the expected type and attempting to convert fails; or
            the value is not of an expected numeric type, is of some other numeric type, has a converted value
            successfully obtained via the conversion callabl, and is not equal to the converted value.
        ValueError
            If, when the value is present and not of the expected type, an invalid conversion callable is used
            successfully to create a converted value that is still not of the expected type.
        """
        if key not in json_obj:
            if required_present:
                raise RuntimeError("Parsed value key '{}' not found while deserializing {}".format(key, cls.__name__))
            else:
                return None
        value = json_obj[key]
        # If the value read is the right type, finish here
        if isinstance(value, expected_type):
            return value
        # Otherwise, try converting if converter callable was supplied
        try:
            if value is None or converter is None:
                raise RuntimeError('caught and another thrown in except')
            converted_value = converter(value)
        except:
            raise RuntimeError(cls._get_invalid_type_message().format(key, expected_type, value.__class__.__name__))
        # Sanity check that the converted value is of the correct type
        if not isinstance(converted_value, expected_type):
            msg = 'Received and used converter callable for parsing serialized JSON that outputs wrong type - '
            msg += 'expected: {}, output: {}'.format(expected_type.__name__, converted_value.__class__.__name__)
            raise ValueError(msg)
        # Finally, be careful when dealing with both numeric values that converted is actually equal to original
        if isinstance(converted_value, Number) and isinstance(value, Number) and value != converted_value:
            msg = cls._get_invalid_type_message() + '(loss of precise value occurs in converting)'
            raise RuntimeError(msg.format(key, expected_type, value.__class__.__name__))
        # If we get this far, then return the converted value
        return converted_value

    @abstractmethod
    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Get the representation of this instance as a serialized dictionary or dictionary-like object (e.g., a JSON
        object).

        Since the returned value must be serializable and JSON-like, key and value types are restricted.  In particular,
        the returned value type, which this docstring will call ``D``, must adhere to the criteria defined below:

        * ``D`` : a ``dict`` with ``str`` keys and with all values being of some type within the defined set ``T``
        * ``T`` : a set of types containing the following:
            * ``str``
            * ::class:``Number`
            * ``D``
            * ``list`` with all elements being some type within the defined set ``T``

        Returns
        -------
        Dict[str, Union[str, Number, dict, list]]
            The representation of this instance as a serialized dictionary or dictionary-like object, with valid types
            of keys and values.
        """
        pass

    def __str__(self):
        return str(self.to_json())

    def to_json(self) -> str:
        """
        Get the representation of this instance as a serialized JSON-formatted string.

        Returns
        -------
        json_string
            the serialized JSON string representation of this instance
        """
        return json.dumps(self.to_dict(), sort_keys=True)


class SerializedDict(Serializable):
    """
    A basic encapsulation of a dictionary as a ::class:`Serializable`.
    """

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        return cls(json_obj)

    def __init__(self, base_dict: dict):
        self.base_dict = base_dict

    def to_dict(self) -> dict:
        return self.base_dict


class ResultIndicator(Serializable, ABC):
    """
    A type extending from ::class:`Serializable` for encapsulating a status indication for a result of something.

    Parameters
    ----------
    success : bool
        Whether this indicates a successful result.
    reason : str
        A very short, high-level summary of the result.
    message : str
        An option, more detailed explanation of the result, which by default is an empty string.

    Attributes
    ----------
    success : bool
        Whether this indicates a successful result.
    reason : str
        A very short, high-level summary of the result.
    message : str
        An option, more detailed explanation of the result, which by default is an empty string.

    """

    def __init__(self, success: bool, reason: str, message: str = '', *args, **kwargs):
        super(ResultIndicator, self).__init__(*args, **kwargs)
        self.success: bool = success
        """ Whether this indicates a successful result. """
        self.reason: str = reason
        """ A very short, high-level summary of the result. """
        self.message: str = message
        """ An option, more detailed explanation of the result, which by default is an empty string. """

    def to_dict(self) -> dict:
        return {'success': self.success, 'reason': self.reason, 'message': self.message}


class BasicResultIndicator(ResultIndicator):
    """
    Bare-bones, concrete implementation of ::class:`ResultIndicator`.
    """

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            return cls(success=json_obj['success'], reason=json_obj['reason'], message=json_obj['message'])
        except Exception as e:
            return None

    def __init__(self, *args, **kwargs):
        super(BasicResultIndicator, self).__init__(*args, **kwargs)