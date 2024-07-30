from abc import ABC, abstractmethod
from ..subset import SubsetDefinition


class ForcingDataHandler(ABC):

    @abstractmethod
    async def is_data_available(self, subset: SubsetDefinition) -> bool:
        """
        Determine and return whether data is available for the given subset.

        Determine whether all necessary data for all the catchments and over the required time period can be provided
        by the forcing service, where those parameters are encapsulated by a ::class:`ForcingSubset` parameter object.

        Note that "available" means only that the required data is somewhere accessible and in some acceptable format.
        E.g., an implementation may be as a proxy of forcing data from an external service.  It may also convert the
        external data from another format to the internal representation, and/or potentially cache data locally after
        this has been done.  In this example, it is not necessary for the external data to have already been retrieve,
        converted, and/or cached to be considered available (although those would also be sufficient conditions).
        This object only needs to be able to determine the external service can provide all the required "raw" data.

        Parameters
        ----------
        subset : SubsetDefinition
            An encapsulation of the forcing subset for which the availability is of interest.

        Returns
        -------
        bool
            Whether data is available for the given subset.
        """
        pass

    @abstractmethod
    def is_data_immediately_available(self, subset: SubsetDefinition) -> bool:
        """
        Determine and return whether data is immediately available for the given subset.

        This is similar to ::method:`is_data_available`, except that implementations will impose some kind of more
        strict locality and/or readiness requirements.  Exactly what those are will vary from implementation to
        implementation and should be clearly documented.

        For example, for a subclass that caches data from an external forcing service and works as a proxy, its version
        of::method:`is_data_available` should return ``True`` for some subset if data is available from the external
        source.  However, this method may return ``False`` for the same subset if, e.g., data was not already locally
        cached.

        Parameters
        ----------
        subset : SubsetDefinition
            An encapsulation of the forcing subset for which the availability is of interest.

        Returns
        -------
        bool
            Whether data is immediately available for the given subset.
        """
        pass

    @abstractmethod
    async def preprocess(self):
        """
        Perform any required data preprocessing for the service to operate.

        An example might be resampling grid-based AORC data to an internal, catchment-base representation.

        Alternatively, a simpler example might be just pre-populating metadata to fulfill calls to
        ::method:`is_data_available` more quickly.
        """
        pass
