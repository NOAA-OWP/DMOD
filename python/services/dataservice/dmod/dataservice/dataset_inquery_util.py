from dmod.core.meta_data import DataFormat, DataRequirement
from dmod.core.serializable import BasicResultIndicator
from dmod.modeldata.data.object_store_manager import Dataset, DatasetType, DatasetManager
from dmod.scheduler.job import Job
from typing import Dict, List, Optional, Tuple
from .data_derive_util import DataDeriveUtil

import logging


class DatasetInqueryUtil:
    """
    Utility class used by main ``dataservice`` manager for dataset detail queries and searches.

    Utility encapsulates behavior with respect to searching for qualifying datasets, determining if specified data is
    available, providing details on where requested data exists, and other queries into existing data and datasets. Note
    that it does not include behavior on retrieving data.
    """

    def __init__(self, data_mgrs_by_ds_type: Dict[DatasetType, DatasetManager],
                 derive_util: Optional[DataDeriveUtil] = None):
        self._all_data_managers: Dict[DatasetType, DatasetManager] = data_mgrs_by_ds_type
        self._derive_util: DataDeriveUtil = DataDeriveUtil(data_mgrs_by_ds_type) if derive_util is None else derive_util

    def _get_known_datasets(self) -> Dict[str, Dataset]:
        """
        Get real-time mapping of all datasets known to this instance via its managers, in a map keyed by dataset name.

        This is implemented as a function, and not a property, since it is mutable and could change without this
        instance or even the service manager being directly notified.  As such, a new collection object is created and
        returned on every call.

        Returns
        -------
        Dict[str, Dataset]
            All datasets known to the service via its manager objects, in a map keyed by dataset name.
        """
        datasets = {}
        for _, manager in self._all_data_managers.items():
            datasets.update(manager.datasets)
        return datasets

    # TODO: (later) in the future, this may also need to be able to check authorization/ownership/permissions
    async def async_can_provide_data(self, dataset_name: str, data_item_name: str) -> BasicResultIndicator:
        """
        Async check if requested data from the described source location can be provided.

        Check, asynchronously, whether the specified data can be provided. The data is specified via a name for the
        containing dataset and a name (or analogous identifier) for the data's "data item."  The exact details of what
        constitutes a "data item" vary depending on the dataset type; frequently, a "data item" is analogous to a file,
        and thus the item name is its relative path.

        For the data to be considered "providable," one of the managers must manage a dataset of the given name, and
        this dataset must have a data item with the provided name/identifier.

        Parameters
        ----------
        dataset_name : str
            The name of the ::class:`Dataset` containing the data.
        data_item_name : str
            The name or identifier of the "data item" containing the desired data within the applicable dataset.

        Returns
        -------
        BasicResultIndicator
            A result object indicating through its ``success`` property whether the referenced data can be provided and,
            if not, some details on why.
        """
        dataset = self._get_known_datasets().get(dataset_name)
        if dataset is None:
            msg = "Data cannot be provided from unknown dataset '{}'".format(dataset_name)
            return BasicResultIndicator(success=False, reason="Unknown Dataset", message=msg)
        elif data_item_name not in dataset.manager.list_files(dataset_name):
            msg = "No file/item named '{}' exist within the '{}' dataset".format(data_item_name, dataset_name)
            return BasicResultIndicator(success=False, reason="Data Item Does Not Exist", message=msg)
        else:
            return BasicResultIndicator(success=True, reason='Valid Dataset and Item')

    async def async_find_dataset_for_requirement(self, requirement: DataRequirement) -> Optional[Dataset]:
        """
        Asynchronously search for an existing dataset that will fulfill the given requirement.

        This function essentially just provides an async wrapper around the synchronous analog.

        Parameters
        ----------
        requirement : DataRequirement
            The data requirement that needs to be fulfilled.

        Returns
        -------
        Optional[Dataset]
            The (first) dataset fulfilling the given requirement, if one is found; otherwise ``None``.

        See Also
        -------
        ::method:`find_dataset_for_requirement`
        """
        return self.find_dataset_for_requirement(requirement)

    async def can_be_fulfilled(self, requirement: DataRequirement, job: Optional[Job] = None) -> Tuple[bool, Optional[Dataset]]:
        """
        Determine details of whether a data requirement can be fulfilled, either directly or by deriving a new dataset.

        The function will process and return a tuple of two items.  The first is whether the data requirement can be
        fulfilled, given the currently existing datasets.  The second is either the fulfilling ::class:`Dataset`, if a
        dataset already exists that completely fulfills the requirement, or ``None``.

        Even if a single fulfilling dataset for the requirement does not already exist, it may still be possible for the
        service to derive a new dataset that does fulfill the requirement.  In such cases, ``True, None`` is returned.

        Parameters
        ----------
        requirement : DataRequirement
            The data requirement in question that needs to be fulfilled.
        job : Optional[Job]
            The job having the given requirement.

        Returns
        -------
        Tuple[bool, Optional[Dataset]]
            A tuple of whether the requirement can be fulfilled and, if one already exists, the fulfilling dataset.
        """
        fulfilling_dataset = await self.async_find_dataset_for_requirement(requirement)
        if isinstance(fulfilling_dataset, Dataset):
            return True, fulfilling_dataset
        else:
            return await self._derive_util.async_can_dataset_be_derived(requirement=requirement, job=job), None

    def find_dataset_for_requirement(self, requirement: DataRequirement) -> Optional[Dataset]:
        """
        Search for an existing dataset that will fulfill the given requirement.

        Parameters
        ----------
        requirement : DataRequirement
            The data requirement that needs to be fulfilled.

        Returns
        -------
        Optional[Dataset]
            The (first) dataset fulfilling the given requirement, if one is found; otherwise ``None``.
        """
        # Keep track of a few things for logging purposes
        datasets_count_match_category = 0
        datasets_count_match_format = 0
        # Keep those of the right category but wrong format, in case one is needed and satisfactory
        potentially_compatible_alternates: List[Dataset] = []

        for name, dataset in self._get_known_datasets().items():
            # Skip anything with the wrong category
            if dataset.category != requirement.category:
                continue

            # Keep track of how many of the right category there were for error purposes
            datasets_count_match_category += 1

            # Skip (for now at least) anything with a different format (though set aside if potentially compatible)
            if dataset.data_format != requirement.domain.data_format:
                # Check if this format could fulfill
                if DataFormat.can_format_fulfill(needed=requirement.domain.data_format, alternate=dataset.data_format):
                    # We will return to examine these if no dataset qualifies that has the exact format in requirement
                    potentially_compatible_alternates.append(dataset)
                continue

            # When a dataset matches, keep track for error counts, and then test to see if it qualifies
            datasets_count_match_format += 1
            # TODO: need additional test of some kind for cases when the requirement specifies "any" (e.g., "any"
            #  catchment (from hydrofabric) in realization config, for finding a forcing dataset)
            if dataset.data_domain.contains(requirement.domain):
                return dataset

        # At this point, no datasets qualify against the exact domain (including format) of the requirement
        # However, before failing, check if any have different, but compatible format, and otherwise qualify
        for dataset in potentially_compatible_alternates:
            if dataset.data_domain.contains(requirement.domain):
                return dataset

        # Before failing, treat the count of alternates as being of the same format, for error messaging purposes
        datasets_count_match_format += len(potentially_compatible_alternates)

        if datasets_count_match_category == 0:
            msg = "Could not fill requirement for '{}': no datasets for this category"
            logging.error(msg.format(requirement.category.name))
        elif datasets_count_match_format == 0:
            msg = "Could not fill requirement with '{}' format domain: no datasets found this (or compatible) format"
            logging.error(msg.format(requirement.domain.data_format.name))
        else:
            msg = "Could not find dataset meeting all restrictions of requirement: {}"
            logging.error(msg.format(requirement.to_json()))
        return None

    def get_dataset_names(self, sort_result: bool = False) -> List[str]:
        """
        Get the names of all current datasets, optionally in sorted order.

        Parameters
        ----------
        sort_result : bool
            Whether to return a sorted list of dataset names (by default ``False``).

        Returns
        -------
        List[str]
            A list of the names of all currently existing datasets.
        """
        results = self._get_known_datasets().keys()
        return sorted(results) if sort_result else results

