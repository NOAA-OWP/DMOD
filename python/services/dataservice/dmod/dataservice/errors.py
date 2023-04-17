from enum import Enum
from http import HTTPStatus


class Error(str, Enum):
    """Error variants and associated metadata.

    # `name` property
    # error name
    DATASET_EXISTS = (

        # `name` property
        # url to error variant info page
        "/error/dataset_exists",

        # `status` property
        # associated HTTP status code
        HTTPStatus.FORBIDDEN,

        # `detail` property
        # descriptive message
        "Dataset already exists",
    )

    """

    DATASET_EXISTS = (
        "/error/dataset_exists",
        HTTPStatus.FORBIDDEN,
        "Dataset already exists",
    )
    DATASET_DOES_NOT_EXIST = (
        "/error/dataset_does_not_exist",
        # TODO: there might be a better status for this
        HTTPStatus.FORBIDDEN,
        "Dataset does not exist",
    )
    DATASET_DOMAIN_NOT_PROVIDED = (
        "/error/dataset_domain_not_provided",
        HTTPStatus.BAD_REQUEST,
        "Dataset domain was not provided",
    )

    PUT_OBJECT_FAILURE = (
        "/error/put_object_failure",
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "Failed to store object",
    )

    def __new__(cls, type: str, status: HTTPStatus, detail: str):
        # if type is: "/error/put_object_failure"
        # value is: "put_object_failure"
        value = type[len("/error/") :].lower()
        obj = str.__new__(cls, value)
        obj._value_ = value

        obj._type = type
        obj._status = status
        obj._detail = detail
        return obj

    @property
    def type(self) -> str:
        # see __new__
        return self._type  # type: ignore

    @property
    def status(self) -> HTTPStatus:
        # see __new__
        return self._status  # type: ignore

    @property
    def detail(self) -> str:
        # see __new__
        return self._detail  # type: ignore
