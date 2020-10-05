#!/usr/bin/env python3

import logging
from requests.exceptions import ReadTimeout
import docker
import yaml
from typing import List, TYPE_CHECKING, Tuple

## local imports
from .utils import parsing_nested as pn

# Imports strictly for type hinting
if TYPE_CHECKING:
    from .job import Job


class DockerServiceParameters():
    def __init__(self, image_tag: str = None, constraints: list = [], hostname: str = None, \
                 labels: dict = {}, serv_name: str = None, mounts: list = []):
        """
        Parameters
        ----------
        image_tag
            image parameter for client.services.create()
        constraints
            constraints parameter for client.services.create()
        hostname
            hostname parameter for client.services.create()
        labels
            labels parameter for client.services.create()
        name
            name parameter for client.services.create()
        mounts
            mounts parameter for client.services.create()
        """
        self.image_tag = image_tag
        self.constraints = constraints
        self.hostname = hostname
        self.labels = labels
        self.serv_name = serv_name
        self.mounts = mounts


class Launcher:

    def __init__(self, images_and_domains_yaml, docker_client=None, api_client=None, **kwargs):
        """ FIXME
        Parameters
        ----------
        docker_client
            Docker API client
        api_client
            Docker Low-level API client
        """
        self._images_and_domains_yaml = images_and_domains_yaml
        if docker_client:
            self.docker_client = docker_client
            self.api_client = api_client
        else:
            self.checkDocker()
            self.docker_client = docker.from_env()
            self.api_client = docker.APIClient()

        #FIXME make networks, stack name __init__ params

        self.constraints = []
        self.hostname = "{{.Service.Name}}"

        #FIXME parameterize network
        self.networks = ["mpi-net"]

    def create_service(self, serviceParams: DockerServiceParameters, idx: int, docker_cmd_args: List[str]) \
        -> docker.from_env().services.create:
        """
        Create new service with Healthcheck, host, and other info

        Parameters
        ----------
        serviceParams
            A DockerServiceParameters class object
        idx
            Index number for labeling a Docker service name
        docker_cmd_args
            Lists of string args to pass to the service, including a string of hostnames and cpus_alloc for running MPI job

        Returns
        -------
        service
            Docker service in Docker API
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client
        # service parameters
        networks = self.networks
        image = serviceParams.image_tag
        constraints = serviceParams.constraints
        hostname = serviceParams.hostname
        serv_labels = serviceParams.labels
        serv_name = serviceParams.serv_name
        mounts = serviceParams.mounts

        Healthcheck = docker.types.Healthcheck(test = ["CMD-SHELL", 'echo Hello'],
                                               interval = 1000000 * 10000 * 1,
                                               timeout = 1000000 * 10000 * 2,
                                               retries = 2,
                                               start_period = 1000000 * 10000)
        # delay 5 minutes before restarting
        # restart = docker.types.RestartPolicy(condition='on-failure')
        restart = docker.types.RestartPolicy(condition='none')

        if (idx == 0): #FIXME just always pass idx???
            docker_cmd_args.append(str(idx))

        try:
            service = client.services.create(image = image,
                                         args = docker_cmd_args,
                                         constraints = constraints,
                                         hostname = hostname,
                                         labels = serv_labels,
                                         name = serv_name,
                                         mounts = mounts,
                                         networks = networks,
                                         # user = user_id,
                                         healthcheck = Healthcheck,
                                         restart_policy=restart)
        except ReadTimeout:
            print("Connection to docker API timed out")
            raise

        self.log_service(serv_name.split("_")[0], service.id)

        return service

    @staticmethod
    def log_service(base_name: str, id: str):
        """
        Log information about service identified by base_name and id

        Parameters
        ----------
        base_name
            str containing the basename of the service, i.e. 'nwm-2.0'
        id
            identifier for the specific service, contatenated to base_name
        """
        #TODO how important is it to inspect/log from the same api/client as launcher is using?
        api_client = docker.APIClient()
        client = docker.from_env()
        from inspect import stack
        inspect = api_client.inspect_service(id, insert_defaults=True)
        logging.info("Output from log_service in {}:".format(stack()[1].function))
        # pp(inspect)
        logging.info("CreatedAt = {}".format(list(pn.find('CreatedAt', inspect))[0]))
        Labels = list(pn.find('Labels', inspect))[0]
        Labels = Labels['com.docker.stack.image']
        (_, Labels) = Labels.split('/')
        (_, HostNode) = ((list(pn.find('Constraints', inspect))[0])[0]).split('==')
        logging.info("HostNode = {}".format(HostNode))
        logging.info("\n")
        # test out some service functions
        serv_list = client.services.list(filters={'name':base_name})[0]
        service_id = serv_list.id
        logging.info("service_id: {}".format(service_id))
        service_name = serv_list.name
        logging.info("service_name: {}".format(service_name))
        service_attrs = serv_list.attrs
        # pp(service_attrs)
        logging.info("\n")
        api_client.close()
        client.close()

    def checkDocker(self):
        """Test that docker is up running"""
        try:
            # Check docker client state
            docker.from_env().ping()
        except:
            raise ConnectionError("Please check that the Docker Daemon is installed and running.")

    @staticmethod
    def build_host_list(job: 'Job') -> str:
        """
        Build a list of string arguments for passing to a started Docker service.

        Build a list of strings for Docker service arguments, consisting of the the container names and the allocated
        CPUs on the associated hosts. Each container's name will correspond to the per-allocation service names,
        accessible via the job's ::attribute:`Job.allocation_service_names` property.

        Parameters
        ----------
        job
            The related job object, which contains an iterable collection of the relevant allocations and analogous
            collection of corresponding service names for the invocations of such allocations.

        Returns
        -------
        str
            Container hosts argument string consisting of newline-separated substrings strings of the format
            ``<host_name>:<num_cores>``.
        """
        num_allocations = len(job.allocations) if job.allocations is not None else 0
        host_str = ''

        if num_allocations > 0:
            for alloc_index in range(num_allocations):
                cpu_count = job.allocations[alloc_index].cpu_count
                host_str += job.allocation_service_names[alloc_index] + ':' + str(cpu_count) + "\n"

        # Finally, strip any trailing newline
        host_str = host_str.rstrip()

        return host_str

    def load_image_and_mounts(self, name: str, version: str, domain: str) -> tuple:
        """ TODO make this a static method, pass in image_and_domain_list file path
        Read a list of image_name and domain_name from the yaml file: image_and_domain.yaml
        Derive domain directory to be used for computing
        The image_name needed and user requested domain_name must be in the list for a valid job request,
        otherwise, it is not supported

        Parameters
        ----------
        name: str
            The name of the model needed to run a user job, must match a top level key in image_and_domain_list
        version:
            The version of the model to use, must match a key under name: version: in image_and_domain_list
        domain:
            The model domain to operate on, must match a key under name: domain: in image_and_domain_list

        Returns
        -------
        selected_image
            The selected image out of the valid image list in the yaml file, there is a match
        mounts: list[str]
            A list of docker style mount strings in the form `selected_domain`:`run_domain`:rw
            The selected domain directory out of the valid domain name : domain directory dicts in the yaml file
        run_domain_dir
            The run domain directory in the docker container, based on the domain name to directory mapping in the yaml file
        """

        # Load the yaml file into dictionary
        with open(self._images_and_domains_yaml) as fn:
            yml_obj = yaml.safe_load(fn)

        try:
            model = yml_obj[name]
        except KeyError:
            raise(KeyError("image_and_domain.yaml has no model key {}".format(name)))
        try:
            domain = model['domains'][domain]
        except KeyError:
            raise(KeyError("image_and_domain.yaml has no domain key {} for model {}".format(domain, name)))
        try:
            run_dir = domain['run']
        except KeyError:
            raise(KeyError("image_and_domain.yaml has no 'run' key for domain {}, model {}".format(domain, name)))
        try:
            local_dir = domain['local']
        except KeyError:
            raise(KeyError("image_and_domain.yaml has no 'local' key for domain {}, model {}".format(domain, name)))
        try:
            image = model['version'][version]
        except KeyError:
            raise(KeyError("image_and_domain.yaml has no version key {}".format(version)))
        try:
            output = model['output']
        except KeyError:
            raise(KeyError("image_and_domain.yaml has no 'output' key for model {}".format(name)))
        try:
            output_local = output['local']
        except KeyError:
            raise(KeyError("image_and_domain.yaml has no `local` key for output, model {}".format(name)))
        try:
            output_run = output['run']
        except KeyError:
            raise(KeyError("image_and_domain.yaml has no `run` key for output, model {}".format(name)))

        #Configure local volume mounts based on domain and model lookup

        input_mount = "{}:{}:rw".format(local_dir, run_dir)
        output_mount = "{}:{}:rw".format(output_local, output_run)

        return image, [input_mount, output_mount]

    def start_job(self, job: 'Job') -> Tuple[bool, tuple]:
        """
        Launch the necessary services to execute the given job, according to its obtained allocations.

        Services/containers will have names corresponding to the values from ::attribute:`Job.allocation_service_names`.
        As a result, they can later be mapped back to the associated job.

        Services themselves are created via a call to ::method:`create_service`.

        Parameters
        ----------
        job: Job
            The job needing to be executed within the runtime environment.

        Returns
        -------
        Tuple[bool, tuple]
            A tuple with the first item being an indication of whether all necessary services were started successfully,
            and the second item being a nested tuple of the service objects returned by ::method:`create_service` as
            they were created.

        See Also
        -------
        ::method:`create_service`
        ::attribute:`Job.allocation_service_names`
        """
        model = job.model_request.get_model_name()
        #FIXME read all image/domain at init and select from internal cache (i.e. dict) or even push to redis for long term cache
        (image_tag, mounts, run_domain_dir) = self.load_image_and_mounts(model,
                                                                         str(job.model_request.version),
                                                                         job.model_request.domain)

        #TODO better align labels/defaults with serviceparam class
        #FIXME if the stack.namespace needs to align with the stack name, this isn't correct
        labels = {"com.docker.stack.image": image_tag, "com.docker.stack.namespace": model}

        #First arg, number of "nodes"
        args = [str( len(job.allocations) )]
        #Second arg, host string
        args.append(self.build_host_list(job))
        #third arg, job id
        args.append(job.job_id)

        #This seems to be more of a dev check than anything required
        #self.write_hostfile(basename, cpusList)
        num_allocations = len(job.allocations) if job.allocations is not None else 0
        if num_allocations == 0:
            logging.error("Attempting to start job {} that has no allocations".format(str(job.job_id)))
            return False, tuple()

        service_per_allocation = []

        for alloc_index in range(num_allocations):
            alloc = job.allocations[alloc_index]
            constraints_str = "node.hostname == {}".format(alloc.hostname)
            constraints = list(constraints_str.split("/"))

            logging.info("Hostname: {}".format(alloc.hostname))
            #FIXME important that all label values are strings, otherwise docker service create hangs
            labels_tmp = {"Hostname": alloc.hostname, "cpus_alloc": str(alloc.cpu_count)}
            labels.update(labels_tmp)

            serv_name = job.allocation_service_names[alloc_index]

            # Create the docker service
            service_params = DockerServiceParameters(image_tag, constraints, alloc.hostname, labels, serv_name, mounts)
            #TODO check for proper service creation, return False if doesn't work
            service = self.create_service(serviceParams=service_params, idx=alloc_index, docker_cmd_args=host_str)
            service_per_allocation.append(service)

        logging.info("\n")
        return True, tuple(service_per_allocation)
