#!/usr/bin/env python3
from typing import Iterable, Mappable, Union
from abc import ABC, abstractmethod
from redis import Redis, WatchError
import logging

## local imports
from .utils import keynamehelper as keynamehelper
from .utils import generate as generate
from .utils import parsing_nested as pn
from .utils.clean import clean_keys

Max_Redis_Init = 5

logging.basicConfig(
    filename='scheduler.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")

resources = [{'node_id': "Node-0001",
           'Hostname': "***REMOVED***",
           'Availability': "active",
           'State': "ready",
           'CPUs': 18,
           'MemoryBytes': 33548128256
          },
          {'node_id': "Node-0002",
           'Hostname': "***REMOVED***",
           'Availability': "active",
           'State': "ready",
           'CPUs': 96,
           'MemoryBytes': 540483764224
          },
          {'node_id': "Node-0003",
           'Hostname': "***REMOVED***",
           'Availability': "active",
           'State': "ready",
           'CPUs': 96,
           'MemoryBytes': 540483764224
          }
         ]

class ResourceManager(ABC):
    """
        Abstract class for defining the API for Resource Managing
    """

    @abstractmethod
    def set_resources(self, resources: Iterable[ Mapping[ str, Union[ str, int] ] ]):
        """
            Set the provided resources into the manager's resource tracker.

            Parameters
            ----------
            resources
                An iterable of maps defining each resource to set.
                One map per resource with the following metadata.
                 { 'node_id': "Node-0001",
                   'Hostname': "my-host",
                   'Availability': "active",
                   'State': "ready",
                   'CPUs': 18,
                   'MemoryBytes': 33548128256
                  }

            Returns
            -------
            None


        """
        pass

    @abstractmethod
    def get_resources(self) -> Iterable[Mappable[str, Union[str, int]]]:
        """
            Get metadata of all managed resoures.

            Returns
            -------
            resources
                An iterable of maps defining each managed resource.
                One map per resource with the following metadata.
                 { 'node_id': "Node-0001",
                   'Hostname': "my-host",
                   'Availability': "active",
                   'State': "ready",
                   'CPUs': 18,
                   'MemoryBytes': 33548128256
                  }

        """
        pass

    @abstractmethod
    def allocate_resource(self, resource_id: str, requested_cpus: int,
                          requested_memory:int =0, partial:bool =False) -> Mappable[str, Union[str, int]]:
      """
        Attemt to allocate the requested resources.  Successful allocation will return
        a non empty map.

        Parameters
        ----------
        resource_id
            Unique ID string of the resource referenceable by the manager

        requested_cpus
            integer numbre of cpus to attempt to allocate

        requested_momory
            integer number of bytes to allocate.  currently optional

        partial
            whether to partially fullfil the requested allocation and return
            an allocation map with less than the requested allocation


      """
      pass

    @abstractmethod
    def release_resources(self, allocated_resources: Iterable[ Mappable[ str, Union[ str, int ] ] ]):
        """
            Give back any allocated resources to the manager.

            Parameters
            ----------
            allocated_resources
                An iterable of maps containing the metadata returned by allocate_resources
        """
        pass
