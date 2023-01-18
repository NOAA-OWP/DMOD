from .message import AbstractInitRequest, MessageEventType, Response
from dmod.core.serializable import Serializable
from .maas_request import ExternalRequest, ExternalRequestResponse
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DataRequirement
from dmod.core.enum import PydanticEnum
from pydantic import root_validator, Field
from numbers import Number
from typing import ClassVar, Dict, Optional, Union, List


class QueryType(PydanticEnum):
    LIST_FILES = 1
    GET_CATEGORY = 2
    GET_FORMAT = 3
    GET_INDICES = 4
    GET_DATA_FIELDS = 5
    GET_VALUES = 6
    GET_MIN_VALUE = 7
    GET_MAX_VALUE = 8

    @classmethod
    def get_for_name(cls, name_str: str) -> 'QueryType':
        """
        Get the enum value corresponding to the given string, ignoring case, and defaulting to ``LIST_FILES``.

        Parameters
        ----------
        name_str : str
            Expected string representation of one of the enum values.

        Returns
        -------
        QueryType
            Enum value corresponding to the given string, or ``LIST_FILES`` if correspondence could not be determined.
        """
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return cls.LIST_FILES


class DatasetQuery(Serializable):

    query_file: QueryType

    def __hash__(self):
        return hash(self.query_type)


class ManagementAction(PydanticEnum):
    """
    Type enumerating the standard actions that can be requested via ::class:`DatasetManagementMessage`.
    """
    UNKNOWN = (-1, False, False)
    """ Placeholder action for when actual action is not known, generally representing an error (e.g., bad parsing). """
    CREATE = (1, True, True, True)
    """ Dataset creation action. """
    ADD_DATA = (2, True, False)
    """ Addition of data to an existing dataset. """
    REMOVE_DATA = (3, True, False)
    """ Removal of data from an existing dataset. """
    DELETE = (4, True, False)
    """ Deletion of an existing dataset. """
    SEARCH = (5, False, True)
    """ Search for dataset(s) satisfying certain conditions (e.g., AORC forcings for right times and catchments). """
    QUERY = (6, True, False)
    """ Query for information about a dataset (e.g., what time period and catchments does a forcing dataset cover). """
    CLOSE_AWAITING = (7, False, False)
    """ Action to close an ongoing, multi-message dialog. """
    LIST_ALL = (8, False, False)
    """ Like ``SEARCH``, but just list all datasets. """
    REQUEST_DATA = (9, True, False)
    """ Action to request data from a dataset, which expect a response with details on how. """

    @classmethod
    def get_for_name(cls, name_str: str) -> 'ManagementAction':
        """
        Get the enum value corresponding to the given string, ignoring case, and defaulting to ``UNKNOWN``.

        Parameters
        ----------
        name_str : str
            Expected string representation of one of the enum values.

        Returns
        -------
        ManagementAction
            Enum value corresponding to the given string, or ``UNKNOWN`` if correspondence could not be determined.
        """
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return cls.UNKNOWN

    def __init__(self, uid: int, requires_name: bool, requires_category: bool, requires_domain: bool = False):
        self._uid = uid
        self._requires_name = requires_name
        self._requires_category = requires_category
        self._requires_domain = requires_domain

    @property
    def requires_data_category(self) -> bool:
        """
        Whether this type of action requires a data category in order for the action to be valid.

        Returns
        -------
        bool
            Whether this type of action requires a data category in order for the action to be valid.

        See Also
        -------
        ::method:`requires_dataset_name`
        """
        return self._requires_category

    @property
    def requires_data_domain(self) -> bool:
        """
        Whether this type of action requires a data domain in order for the action to be valid.

        Returns
        -------
        bool
            Whether this type of action requires a data domain in order for the action to be valid.

        See Also
        -------
        ::method:`requires_dataset_name`
        """
        return self._requires_category

    @property
    def requires_dataset_name(self) -> bool:
        """
        Whether this type of action requires a dataset name in order for the action to be valid.

        Certain actions - e.g., ``CREATE`` - cannot be performed without the name of the dataset involved. However,
        others, such as ``SEARCH``, inherently do not.

        This property provides a convenient way of accessing whether a name is required for a particular enum value's
        action to be performable.

        Returns
        -------
        bool
            Whether this type of action requires a dataset name in order for the action to be valid.
        """
        return self._requires_name


class DatasetManagementMessage(AbstractInitRequest):
    """
    Message type for initiating any action related to dataset management.

    Valid actions are enumerated by the ::class:`ManagementAction`.
    """

    event_type: ClassVar[MessageEventType] = MessageEventType.DATASET_MANAGEMENT

    management_action: ManagementAction = Field(description="The type of ::class:`ManagementAction` this message embodies or requests.")
    dataset_name: Optional[str] = Field(description="The name of the involved dataset, if applicable.")
    is_read_only_dataset: bool = Field(False, description="Whether the dataset involved is, should be, or must be (depending on action) read-only.")
    data_category: Optional[DataCategory] = Field(description="The category of the involved data, if applicable.")
    data_domain: Optional[DataDomain] = Field(description="The domain of the involved data, if applicable.")
    data_location: Optional[str] = Field(description="Location for acted-upon data.")
    is_pending_data: bool = Field(False, description="Whether the sender has data pending transmission after this message.")
    """
    Whether the sender has data it wants to transmit after this message.  The typical use case is during a
    ``CREATE`` action, where this indicates there is already data to add to the newly created dataset.
    """
    query: Optional[DatasetQuery]

    @root_validator()
    def _post_init_validate_dependent_fields(cls, values):
        # Sanity check certain param values depending on the action; e.g., can't CREATE a dataset without a name
        action: ManagementAction = values["management_action"]
        name, category, domain = values["dataset_name"], values["data_category"], values["data_domain"]
        err_msg_template = "Cannot create {} for action {} without {}"
        if name is None and action.requires_dataset_name:
            raise RuntimeError(err_msg_template.format(cls.__name__, action, "a dataset name"))
        if category is None and action.requires_data_category:
            raise RuntimeError(err_msg_template.format(cls.__name__, action, "a data category"))
        if domain is None and action.requires_data_domain:
            raise RuntimeError(err_msg_template.format(cls.__name__, action, "a data domain"))

        return values

    class Config:
        fields = {
            "management_action": {"alias": "action"},
            "data_category": {"alias": "category"},
            "is_read_only_dataset": {"alias": "read_only"},
            "is_pending_data": {"alias": "pending_data"},
        }

    def __eq__(self, other):
        try:
            if not isinstance(self, other.__class__):
                return False
            elif self.dataset_name != other.dataset_name or self.is_read_only_dataset != other.is_read_only_dataset:
                return False
            elif self.data_category != other.data_category:
                return False
            if self.data_domain != other.data_domain:
                return False
            elif self.is_pending_data != other.is_pending_data:
                return False
            elif self.query != other.query:
                return False
            else:
                return True
        except:
            return False

    def __hash__(self):
        return hash('-'.join([self.management_action.name, self.dataset_name, str(self.is_read_only_dataset),
                              self.data_category.name, str(hash(self.data_domain)), self.data_location,
                              str(self.is_pending_data), self.query.to_json()]))

    def __init__(
        self,
        *,
        # NOTE: default is None for backwards compatibility. could be specified using alias.
        action: ManagementAction = None,
        dataset_name: Optional[str] = None,
        is_read_only_dataset: bool = False,
        category: Optional[DataCategory] = None,
        domain: Optional[DataDomain] = None,
        data_location: Optional[str] = None,
        is_pending_data: bool = False,
        query: Optional[DatasetQuery] = None,
        **data
    ):
        """
        Initialize this instance.

        Parameters
        ----------
        action : ManagementAction
            The action this message embodies or requests.
        dataset_name : Optional[str]
            The optional name of the involved dataset, when applicable; defaults to ``None``.
        is_read_only_dataset : bool
            Whether dataset involved is, should be, or must be (depending on action) read-only; defaults to ``False``.
        category : Optional[str]
            The optional category of the involved dataset or datasets, when applicable; defaults to ``None``.
        data_location : Optional[str]
            Optional location/file/object/etc. for acted-upon data.
        is_pending_data : bool
            Whether the sender has data pending transmission after this message (default: ``False``).
        query : Optional[DatasetQuery]
            Optional ::class:`DatasetQuery` object for query messages.
        """
        super().__init__(
            management_action=action or data.pop("management_action", None),
            dataset_name=dataset_name,
            is_read_only_dataset=is_read_only_dataset or data.pop("read_only", False),
            data_category=category or data.pop("data_category", None),
            data_domain=domain or data.pop("data_domain", None),
            data_location=data_location,
            is_pending_data=is_pending_data or data.pop("pending_data", False),
            query=query,
            **data
        )


class DatasetManagementResponse(Response):

    _DATA_KEY_ACTION= 'action'
    _DATA_KEY_DATA_ID = 'data_id'
    _DATA_KEY_DATASET_NAME = 'dataset_name'
    _DATA_KEY_ITEM_NAME = 'item_name'
    _DATA_KEY_QUERY_RESULTS = 'query_results'
    _DATA_KEY_IS_AWAITING = 'is_awaiting'
    response_to_type = DatasetManagementMessage

    def __init__(self, action: Optional[ManagementAction] = None, is_awaiting: bool = False,
                 data_id: Optional[str] = None, dataset_name: Optional[str] = None, data: Optional[dict] = None,
                 **kwargs):
        if data is None:
            data = {}

        # Make sure 'action' param and action string within 'data' param aren't both present and conflicting
        if action is not None:
            if action.name != data.get(self._DATA_KEY_ACTION, action.name):
                msg = '{} initialized with {} action param, but {} action in initial data.'
                raise ValueError(msg.format(self.__class__.__name__, action.name, data.get(self._DATA_KEY_ACTION)))
            data[self._DATA_KEY_ACTION] = action.name
        # Additionally, if not using an explicit 'action', make sure it's a valid action string in 'data', or bail
        else:
            data_action_str = data.get(self._DATA_KEY_ACTION, '')
            # Compare the string to the 'name' string of the action value obtain by passing the string to get_for_name()
            if data_action_str.strip().upper() != ManagementAction.get_for_name(data_action_str).name.upper():
                msg = "No valid action param or within 'data' when initializing {} instance (received only '{}')"
                raise ValueError(msg.format(self.__class__.__name__, data_action_str))

        data[self._DATA_KEY_IS_AWAITING] = is_awaiting
        if data_id is not None:
            data[self._DATA_KEY_DATA_ID] = data_id
        if dataset_name is not None:
            data[self._DATA_KEY_DATASET_NAME] = dataset_name
        super().__init__(data=data, **kwargs)

    @property
    def action(self) -> ManagementAction:
        """
        The action requested by the ::class:`DatasetManagementMessage` for which this instance is the response.

        Returns
        -------
        ManagementAction
            The action requested by the ::class:`DatasetManagementMessage` for which this instance is the response.
        """
        if self._DATA_KEY_ACTION not in self.data:
            return ManagementAction.UNKNOWN
        elif isinstance(self.data[self._DATA_KEY_ACTION], str):
            return ManagementAction.get_for_name(self.data[self._DATA_KEY_ACTION])
        elif isinstance(self.data[self._DATA_KEY_ACTION], ManagementAction):
            val = self.data[self._DATA_KEY_ACTION]
            self.data[self._DATA_KEY_ACTION] = val.name
            return val
        else:
            return ManagementAction.UNKNOWN

    @property
    def data_id(self) -> Optional[str]:
        """
        When available, the 'data_id' of the related dataset.

        Returns
        -------
        Optional[str]
            When available, the 'data_id' of the related dataset.
        """
        return self.data[self._DATA_KEY_DATA_ID] if self._DATA_KEY_DATA_ID in self.data else None

    @property
    def dataset_name(self) -> Optional[str]:
        """
        When available, the name of the relevant dataset.

        Returns
        -------
        Optional[str]
            When available, the name of the relevant dataset; otherwise ``None``.
        """
        return self.data[self._DATA_KEY_DATASET_NAME] if self._DATA_KEY_DATASET_NAME in self.data else None

    @property
    def item_name(self) -> Optional[str]:
        """
        When available/appropriate, the name of the relevant dataset item/object/file.

        Returns
        -------
        Optional[str]
            The name of the relevant dataset item/object/file, or ``None``.
        """
        return self.data.get(self._DATA_KEY_ITEM_NAME)

    @property
    def query_results(self) -> Optional[dict]:
        return self.data.get(self._DATA_KEY_QUERY_RESULTS)

    @property
    def is_awaiting(self) -> bool:
        """
        Whether the response, in addition to success, indicates the response sender is awaiting something additional.

        Typically, this is an indication that the responder side is ready and expecting additional follow-up messages
        from the originator.  For example, after responding to a successful ``CREATE``, a message may set that it is
        in the awaiting state to wait for data to be uploaded by the originator for insertion into the new dataset.

        Returns
        -------
        bool
            Whether the response indicates the response sender is awaiting something additional.
        """
        return self.data[self._DATA_KEY_IS_AWAITING]


class MaaSDatasetManagementMessage(DatasetManagementMessage, ExternalRequest):
    """
    A publicly initiated, and thus session authenticated, extension of ::class:`DatasetManagementMessage`.

    Note that message hashes and equality do not consider session secret, to be compatible with the implementations in
    the superclass.
    """

    data_requirements: List[DataRequirement] = Field(
        default_factory=list,
        description="List of all the explicit and implied data requirements for this request.",
    )
    """
    By default, this is an empty list, though it is possible to append requirements to the list.
    """

    output_formats: List[DataFormat] = Field(
        default_factory=list,
        description="List of the formats of each required output dataset for the requested task."
        )
    """
    By default, this will be an empty list, though if any request does need to produce output,
    formats can be appended to it.
    """

    class Config:
        # NOTE: in parent class, `ExternalRequest`, `session_secret` is aliased using `session-secret`
        fields = {"session_secret": {"alias": "session_secret"}}

    @classmethod
    def factory_create(cls, mgmt_msg: DatasetManagementMessage, session_secret: str) -> 'MaaSDatasetManagementMessage':
        return cls(session_secret=session_secret, action=mgmt_msg.management_action, dataset_name=mgmt_msg.dataset_name,
                   is_read_only_dataset=mgmt_msg.is_read_only_dataset, category=mgmt_msg.data_category,
                   domain=mgmt_msg.data_domain, data_location=mgmt_msg.data_location,
                   is_pending_data=mgmt_msg.is_pending_data)

    @classmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict) -> 'MaaSDatasetManagementResponse':
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        return MaaSDatasetManagementResponse.factory_init_from_deserialized_json(json_obj=json_obj)

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True, # Note this follows Serializable convention
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> Dict[str, Union[str, int]]:
        exclude = exclude or set()

        if not self.data_requirements:
            exclude.add("data_requirements")
        if not self.output_formats:
            exclude.add("output_formats")

        return super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )


class MaaSDatasetManagementResponse(ExternalRequestResponse, DatasetManagementResponse):
    """
    Analog of ::class:`DatasetManagementResponse`, but for the ::class:`MaaSDatasetManagementMessage` message type.
    """

    response_to_type = MaaSDatasetManagementMessage

    @classmethod
    def factory_create(cls, dataset_mgmt_response: DatasetManagementResponse) -> 'MaaSDatasetManagementResponse':
        """
        Create an instance from the non-session-based ::class:`DatasetManagementResponse`.

        Parameters
        ----------
        dataset_mgmt_response : DatasetManagementResponse
            Analogous instance of the non-session type.

        Returns
        -------
        MaaSDatasetManagementResponse
            Factory-created analog of this instance type.
        """
        return cls.factory_init_from_deserialized_json(dataset_mgmt_response.to_dict())
