from functools import lru_cache
from typing import (
    Any,
    ClassVar,
    Dict,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Tuple,
    Type,
    TypeVar,
    ValuesView,
)

from dmod.core.serializable import Serializable
from pydantic import Extra, ValidationError
from typing_extensions import Self

M = TypeVar("M", bound="SerializableDict")


class SerializableDict(Serializable):
    """
    A `Serializable` subtype that implements the `dict`interface. This means you can treat
    `SerializableDict` and it's subtypes as if they were `dict` instances. Likewise,
    `SerializableDict` subclasses are semantically specified equivalently to `Serializable`
    subtypes. However there are subtle divergent behavioral differences between `SerializableDict`,
    `Serializable`, and built-in `dict`:

    `SerializableDict` vs `Serializable`:
        - `SerializableDict` subclasses allow extra, non-validated, fields. Extra fields _are_
        included in serialized form (e.g. `to_dict()`). Toggle the `Config.extra` flag to change
        this behavior.

    `SerializableDict` vs `dict`:
        - `clear()` removes all extra fields; non-extra fields are untouched. As a result, `len()`
        after a `clear()` will not be 0 if the `SerializableDict` has non-fields.

        - Deleting non-extra fields is a `KeyError`. `del` and `pop()` will always raise
        `KeyError`'s if a non-extra field name is provided. Likewise, `popitem()` can also raise a
        `KeyError` if the last item inserted into `__dict__` was a non-extra field or if `__dict__`
        is empty.

        - If `Config.validate_assignment` is **on**, non-extra fields are validated. As a results,
        setting via `[]` (`__setitem__`) or `setdefault()` could raise a `pydantic.ValidationError`
        if validation fails.

        - If `Config.validate_assignment` is **on**, `update()` can raise a
        `pydantic.ValidationError`. However, `update()` _guarantees_ if a `pydantic.ValidationError`
        is thrown, `__dict__` will _not_ be left in a partially updated state. Meaning, the
        pre-`update()` state of `__dict__` will be restored. A performance penalty is taken to
        guarantee this. A deep copy of `__dict__` is taken for roll-back purposes. The
        `update_unsafe()` method is provided if you need to avoid this performance penalty. Note,
        `update_unsafe()` operates the same as `update()` when `Config.validate_assignment` if off.
    """

    __SENTINEL: ClassVar[object] = object()

    class Config:
        extra = Extra.allow

    def __contains__(self, key: str) -> bool:
        return key in self.__dict__

    def __delitem__(self, key: str):
        if key in self.__fields__:
            raise KeyError("Deleting non-extra fields is forbidden.")

        del self.__dict__[key]

    def __getitem__(self, key: str) -> Any:
        return self.__dict__[key]

    def __len__(self) -> int:
        return len(self.__dict__)

    def __setitem__(self, key: str, value: Any):
        if key in self.__fields__:
            # validation is performed if `Config.validate_assignment` flag on
            setattr(self, key, value)
            return

        self.__dict__[key] = value

    def __iter__(self) -> Iterator[str]:
        return self.__dict__.__iter__()

    def clear(self):
        """Remove all non-extra fields"""
        keys_to_remove = set(self.__dict__).difference(self.__fields__)
        for key in keys_to_remove:
            del self.__dict__[key]

    @classmethod
    def fromkeys(cls, iterable: Iterable[Any], value: Any = None) -> Self:
        return cls(**{k: value for k in iterable})

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self:
            return default
        return self[key]

    def items(self) -> ItemsView[str, Any]:
        return self.__dict__.items()

    def keys(self) -> KeysView[str]:
        return self.__dict__.keys()

    def pop(self, key: str, default: Any = __SENTINEL) -> Any:
        if key in self.__fields__:
            raise KeyError("Deleting non-extra fields is forbidden.")

        if default == self.__SENTINEL:
            return self.__dict__.pop(key)

        return self.__dict__.pop(key, default)

    def popitem(self) -> Tuple[str, Any]:
        key, value = self.__dict__.popitem()

        if key in self.__fields__:
            self[key] = value
            raise KeyError("Deleting non-extra fields is forbidden.")

        return key, value

    def setdefault(self, key: str, default: Any = None):
        try:
            return self[key]
        except KeyError:
            self[key] = default

        return default

    def update(self, values: Dict[str, Any]):
        """
        Update the dictionary with the key/value pairs from `values`, overwriting existing keys.

        Note, if `Config.validate_assignment` is **on**, `update()` can raise a
        `pydantic.ValidationError`. However, `update()` _guarantees_ if a `pydantic.ValidationError`
        is thrown, `__dict__` will _not_ be left in a partially updated state. Meaning, the
        pre-`update()` state of `__dict__` will be restored. A performance penalty is taken to
        guarantee this. A deep copy of `__dict__` is taken for roll-back purposes. The
        `update_unsafe()` method is provided if you need to avoid this performance penalty. Note,
        `update_unsafe()` operates the same as `update()` when `Config.validate_assignment` if off.

        Parameters
        ----------
        values : Dict[str, Any]

        Raises
        ------
        ValidationError
            This can only be raised if `Config.validate_assignment` is on.
        """
        validate_assignment = _validate_assignment(type(self))
        # field validation is off. fast branch.
        if not validate_assignment:
            self.update_unsafe(values)
            return

        # field validation is on. It is possible while updating fields that validation fails and
        # `__dict__` is left in a partially updated state. For this reason, `__dict__` must be
        # deep copied.  Then try and update with `values`, if there are exceptions, `__dict__` is
        # replaced with the copy.
        import copy

        original_state = copy.deepcopy(self.__dict__)

        try:
            for key, value in values.items():
                self[key] = value
        except ValidationError as e:
            # `pydantic.BaseModel.__setattr__` overload embeds __dict__ within __dict__ if set
            # through it's `__setattr__`. use object's __setattr__ to get around this.
            object.__setattr__(self, "__dict__", original_state)
            raise e

    def update_unsafe(self, values: Dict[str, Any]):
        """
        Update the dictionary with the key/value pairs from `values`, overwriting existing keys even
        if `Config.validate_assignment` is on. Field validation will not be performed even if
        `Config.validate_assignment` flag is on. Use `update()` if `Config.validate_assignment` is
        **off** -- there is no benefit to using this method.

        Parameters
        ----------
        values : Dict[str, Any]
        """
        self.__dict__.update(values)

    def values(self) -> ValuesView[Any]:
        return self.__dict__.values()


@lru_cache(maxsize=None)
def _validate_assignment(cls: Type[M]) -> bool:
    validate_assignment: bool = False

    # base case
    if cls == Serializable:
        return validate_assignment

    super_classes = cls.__mro__
    base_class_index = super_classes.index(Serializable)

    # index 0 is the calling cls.
    # walk to mro in reverse order from superclasses up until cls (stopping condition).
    #
    # _toggle_ `validate_assignment` flag if set in superclasses.
    for s in super_classes[1:base_class_index][::-1]:
        if not issubclass(s, Serializable):
            continue

        # doesn't have a Config class or Config.validate_assignment
        if not hasattr(s, "Config") and not hasattr(s.Config, "validate_assignment"):
            continue

        validate_assignment = _validate_assignment(s)

    # has Config class and Config.validate_assignment
    if hasattr(cls, "Config") and hasattr(cls.Config, "validate_assignment"):
        validate_assignment = cls.Config.validate_assignment

    return validate_assignment
