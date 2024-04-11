import dataclasses
from typing import Dict, Iterable, Tuple

from dmod.core.dataset import Dataset, DatasetManager, DatasetType
from dmod.core.exception import DmodRuntimeError


@dataclasses.dataclass
class DatasetManagerCollection:
    """
    Collection of DatasetManager objects and their associated DatasetType.
    For each DatasetType, there must be only one DatasetManager.
    A given DatasetManager instance may be associated with multiple DatasetTypes.
    """
    _managers: Dict[DatasetType, DatasetManager] = dataclasses.field(
        default_factory=dict, init=False
    )

    def __hash__(self) -> int:
        return id(self)

    def manager(self, dataset_type: DatasetType) -> DatasetManager:
        """
        Return the manager for the given dataset type.

        Parameters
        ----------
        dataset_type : DatasetType

        Returns
        -------
        DatasetManager
            Manager Associated with the given dataset type.

        Raises
        ------
        KeyError
            If there is not a manager for the given dataset type.
        """
        return self._managers[dataset_type]

    def managers(self) -> Iterable[Tuple[DatasetType, DatasetManager]]:
        """
        Iterable of all managers in collection as tuples of (DatasetType, DatasetManager).

        Returns
        -------
        Iterable[Tuple[DatasetType, DatasetManager]]
        """
        return ((t, m) for (t, m) in self._managers.items())

    def add(self, manager: DatasetManager) -> None:
        """
        Add a manager. If a manager with the same UUID is already in the collection, it ignored.

        Parameters
        ----------
        manager : DatasetManager

        Raises
        ------
        DmodRuntimeError
            If a manager for the same DatasetType already exists.
        DmodRuntimeError
            If the manager to be added has a dataset with a name that duplicates the name of a known dataset from one of this instance's other managers.
        """
        # In this case, just return, as the manager is already added
        if manager.uuid in set(m.uuid for m in self._managers.values()):
            return

        known_dataset_names = set(self.known_datasets().keys())
        if not known_dataset_names.isdisjoint(manager.datasets.keys()):
            duplicates = known_dataset_names.intersection(manager.datasets.keys())
            msg = "Can't add {} to service with already known dataset names {}."
            raise DmodRuntimeError(msg.format(manager.__class__.__name__, duplicates))

        if not manager.supported_dataset_types.isdisjoint(self._managers.keys()):
            duplicates = manager.supported_dataset_types.intersection(
                self._managers.keys()
            )
            msg = "Can't add new {} to service for managing already managed dataset types {}."
            raise DmodRuntimeError(msg.format(manager.__class__.__name__, duplicates))

        for dataset_type in manager.supported_dataset_types:
            self._managers[dataset_type] = manager

    def known_datasets(self) -> Dict[str, Dataset]:
        """
        Get real-time mapping of all datasets known to this instance via its managers, in a map keyed by dataset name.

        This is implemented as a function, and not a property, since it is mutable and could change without this service
        instance being directly notified.  As such, a new collection object is created and returned on every call.

        Returns
        -------
        Dict[str, Dataset]
            All datasets known to the service via its manager objects, in a map keyed by dataset name.
        """
        datasets: Dict[str, Dataset] = {}
        for manager in self._managers.values():
            datasets.update(manager.datasets)
        return datasets
