from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime
from dmod.communication.serializeable import Serializable
from numbers import Number
from typing import Dict, Generic, Optional, Tuple, Type, TypeVar, Union
from ..subset import SubsetDefinition

DOMAIN_PARAM_TYPE = TypeVar('DOMAIN_PARAM_TYPE')


class DataFormat(Enum):
    AORC_CSV = (0,)
    """ The CSV data format the Nextgen framework originally used during its early development. """
    NETCDF_FORCING_CANONICAL = (1,)
    """ The Nextgen framework "canonical" NetCDF forcing data format. """
    NETCDF_AORC_DEFAULT = (2,)
    """ The default format for "raw" AORC forcing data. """
    # TODO: need to specify the particular data property fields for given formats
    # TODO: need format specifically for Nextgen model output (i.e., for evaluations)

    @classmethod
    def get_for_name(cls, name_str: str) -> Optional['DataFormat']:
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return None

    def __init__(self, uid: int, data_fields: Optional[Dict[str, Type]] = None):
        self._uid = uid
        self._data_fields = data_fields

    @property
    def data_fields(self) -> Optional[Dict[str, Type]]:
        """
        The specific data fields for this format.

        Returns
        -------
        Optional[Dict[str, Type]]
            The specific data fields for this format.
        """
        return self._data_fields


class DataCategory(Enum):
    """
    The general category values for different data.
    """
    FORCING = 0
    HYDROFABRIC = 1
    OUTPUT = 2
    OBSERVATION = 3

    @classmethod
    def get_for_name(cls, name_str: str) -> Optional['DataCategory']:
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return None


class TimeRange(Serializable):
    """
    Encapsulated representation of a time range.
    """

    SERIAL_DATETIME_STR_FORMAT = '%Y-%m-%d %H:%M:%S'

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            return cls(range_begin=datetime.strptime(json_obj['range_begin'], cls.SERIAL_DATETIME_STR_FORMAT),
                       range_end=datetime.strptime(json_obj['range_end'], cls.SERIAL_DATETIME_STR_FORMAT))
        except:
            return None

    def __init__(self, range_begin: datetime, range_end: datetime):
        self.range_begin = range_begin
        self.range_end = range_end

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = {}
        serial['range_begin'] = self.range_begin.strftime(self.SERIAL_DATETIME_STR_FORMAT)
        serial['range_end'] = self.range_end.strftime(self.SERIAL_DATETIME_STR_FORMAT)
        return serial


class DataRequirement(Serializable, ABC, Generic[DOMAIN_PARAM_TYPE]):
    """
    A definition of a particular data requirement needed for an execution task.
    """

    _KEY_CATEGORY = 'category'
    """ Serialization dictionary JSON key for ::attribute:`category` property value. """
    _KEY_DOMAIN_PARAMS = 'domain_params'
    """ Serialization dictionary JSON key for ::attribute:`domain_params` property value. """
    _KEY_FULFILLED_BY = 'fulfilled_by'
    """ Serialization dictionary JSON key for ::attribute:`fulfilled_by` property value. """
    _KEY_IS_INPUT = 'is_input'
    """ Serialization dictionary JSON key for ::attribute:`is_input` property value. """
    _KEY_REQ_SUBTYPE = 'requirement_type'
    """ Serialization dictionary JSON key for field to indicate the specific subtype class that was serialized. """
    _KEY_SIZE = 'size'
    """ Serialization dictionary JSON key for ::attribute:`size` property value. """
    _KEY_TIME_PARAMS = 'time_params'
    """ Serialization dictionary JSON key for ::attribute:`time_params` property value. """

    @classmethod
    def _deserialize_common(cls, json_obj: dict) -> Tuple[
            DataCategory, bool, Optional[TimeRange], Optional[str], Optional[int]]:
        """
        Deserialize a common collection of property values for various subtypes, and return in a tuple.

        Parameters
        ----------
        json_obj : dict
            JSON for a complete serialized representation of an instance.

        Returns
        -------
        Tuple[DataCategory, bool, Optional[TimeRange], Optional[str], Optional[int]]
            Tuple of deserialized values of data category, is_input, time_params, fulfilled_by dataset name, and size.
        """
        category = DataCategory.get_for_name(json_obj[cls._KEY_CATEGORY])
        is_input = json_obj[cls._KEY_IS_INPUT]
        if cls._KEY_TIME_PARAMS in json_obj:
            time_params = TimeRange.factory_init_from_deserialized_json(json_obj[cls._KEY_TIME_PARAMS])
        else:
            time_params = None
        fulfilled_by = json_obj[cls._KEY_FULFILLED_BY] if cls._KEY_FULFILLED_BY in json_obj else None
        size = json_obj[cls._KEY_SIZE] if cls._KEY_SIZE in json_obj else None
        return category, is_input, time_params, fulfilled_by, size

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional['DataRequirement']:
        """
        Deserialize the given JSON to a ::class:`DataRequirement` instance, or return ``None`` if it is not valid.

        Implementation recursively searches for the appropriate subtype class based on the value of the subclass name.
        It then calls that class's implementation of this function and returns the value.

        The subclass name is serialized under the ::attribute:`_KEY_REQ_SUBTYPE` serialization key; i.e., accessible via
        the ``_KEY_REQ_SUBTYPE`` class attribute.

        A safeguard is provided to prevent recursively calling this function again in cases when the found subtype does
        not provide its own override implementation.  In such cases, ``None`` is returned.

        Parameters
        ----------
        json_obj : dict
            The JSON to be deserialized.

        Returns
        -------
        Optional[DataRequirement]
            A deserialized ::class:`DataRequirement` instance, or return ``None`` if the JSON is not valid.
        """
        # Bail if we can't even begin to determine the right subclass to deserialize
        if cls._KEY_REQ_SUBTYPE not in json_obj:
            return None

        # Avoid recursive infinite loop by adding an indicator key and bailing if we already see it
        # This happens when the subtype doesn't provide its own implementation of this function (and so uses this one)
        recursive_loop_key = 'base_type_invoked_twice'
        if recursive_loop_key in json_obj:
            # TODO: consider some kind of default serialization
            return None
        else:
            json_obj[recursive_loop_key] = True

        # Traverse recursively to find all subclasses, searching for the one matching the expected serialized type name
        expected_subtype = json_obj[cls._KEY_REQ_SUBTYPE]
        subclasses = []                 # A queue of subclasses to process
        traversed_subclasses = set()    # A queue of subclasses that have already been examined

        subclasses.extend(cls.__subclasses__())
        while len(set(subclasses)) > len(traversed_subclasses):
            for subclass in subclasses:
                if subclass not in traversed_subclasses:
                    if subclass.__name__ == expected_subtype:
                        # Once we have the result back, remove the recursive loop key guard
                        deserialized = subclass.factory_init_from_deserialized_json(json_obj)
                        json_obj.pop(recursive_loop_key)
                        return deserialized
                    else:
                        subclasses.extend(subclass.__subclasses__())
                        traversed_subclasses.add(subclass)
        # Again, if we arrive here, the risk of recursive subtype calls is over, so remove the recursive loop key guard
        json_obj.pop(recursive_loop_key)
        return None

    def __init__(self, domain_params: DOMAIN_PARAM_TYPE, is_input: bool, category: DataCategory,
                 time_params: Optional[TimeRange] = None, size: Optional[int] = None,
                 fulfilled_by: Optional[str] = None):
        self._domain_params = domain_params
        self._is_input = is_input
        self._category = category
        self._time_params = time_params
        self._size = size
        self._fulfilled_by = fulfilled_by

    @property
    def category(self) -> DataCategory:
        """
        The ::class:`DataCategory` of data required.

        Returns
        -------
        DataCategory
            The category of data required.
        """
        return self._category

    @property
    def domain_params(self) -> DOMAIN_PARAM_TYPE:
        """
        Parameters for defining the domain of the required data.

        Note that time-based params should be handled separately by ::attribute:`time_params`.  Also, data fields
        details should also be handled implicitly by being encoded within the ::attribute:`category` property value.

        Returns
        -------
        DOMAIN_PARAM_TYPE
            The domain parameters object.
        """
        return self._domain_params

    @property
    def fulfilled_by(self) -> Optional[str]:
        """
        The name of the dataset that will fulfill this, if it is known.

        Returns
        -------
        Optional[str]
            The name of the dataset that will fulfill this, if it is known; ``None`` otherwise.
        """
        return self._fulfilled_by

    @fulfilled_by.setter
    def fulfilled_by(self, name: str):
        self._fulfilled_by = name

    @property
    def is_input(self) -> bool:
        """
        Whether this represents required input data, as opposed to a requirement for storing output data.

        Returns
        -------
        bool
            Whether this represents required input data.
        """
        return self._is_input

    @abstractmethod
    def serialize_domain_params(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Serialize ::attribute:`domain_params` in a way consistent with ::method:`Serializable.to_dict()`.

        Returns
        -------
        Dict[str, Union[str, Number, dict, list]]
            The serialized form of ::attribute:`domain_params`.
        """
        pass

    @property
    def size(self) -> Optional[int]:
        """
        The size of the required data, if it is known.

        This is particularly important (though still not strictly required) for an output data requirement; i.e., a
        requirement to store output data somewhere.

        Returns
        -------
        Optional[int]
            he size of the required data, if it is known, or ``None`` otherwise.
        """
        return self._size

    @property
    def time_params(self) -> Optional[TimeRange]:
        """
        Time range parameters for this required data, if applicable.

        Returns
        -------
        Optional[TimeRange]
            Time range parameters for this required data, if applicable.
        """
        return self._time_params

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = {}
        serial[self._KEY_REQ_SUBTYPE] = self.__class__.__name__
        serial[self._KEY_DOMAIN_PARAMS] = self.serialize_domain_params()
        serial[self._KEY_IS_INPUT] = self.is_input
        serial[self._KEY_CATEGORY] = self.category.name
        if self.size is not None:
            serial[self._KEY_SIZE] = self.size
        if self.time_params is not None:
            serial[self._KEY_TIME_PARAMS] = self.time_params
        if self.fulfilled_by is not None:
            serial[self._KEY_FULFILLED_BY] = self.fulfilled_by
        return serial


class CatchmentDataRequirement(DataRequirement[SubsetDefinition]):
    """
    Extension of ::class:`DataRequirement` over some domain of catchments.

    Type uses a ::class:`SubsetDefinition` object for its domain parameters, as this effectively encapsulates a
    collection of catchments.
    """

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional['CatchmentDataRequirement']:
        """
        Deserialize JSON to a ::class:`CatchmentDataRequirement` instance, or return ``None`` if it is not valid.

        Parameters
        ----------
        json_obj : dict
            The JSON to be deserialized.

        Returns
        -------
        Optional[CatchmentDataRequirement]
            A deserialized ::class:`CatchmentDataRequirement` instance, or return ``None`` if the JSON is not valid.
        """
        try:
            category, is_input, time_params, fulfilled_by, size = cls._deserialize_common(json_obj)
            domain_params = SubsetDefinition.factory_init_from_deserialized_json(json_obj[cls._KEY_DOMAIN_PARAMS])
            return cls(is_input=is_input, domain_params=domain_params, time_params=time_params, category=category,
                       fulfilled_by=fulfilled_by, size=size)
        except:
            return None

    def serialize_domain_params(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Serialize ::attribute:`domain_params` in a way consistent with ::method:`Serializable.to_dict()`.

        For this type, since ::attribute:`domain_params` is of a ::class:`Serializable` subtype, the standard
        serialization mechanisms are used.

        Returns
        -------
        Dict[str, Union[str, Number, dict, list]]
            The serialized form of ::attribute:`domain_params`.
        """
        return self.domain_params.to_dict()
