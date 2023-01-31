#!/usr/bin/env python3

import logging
from requests.exceptions import ReadTimeout
from dmod.communication import MessageEventType, NGENRequest, NWMRequest
from dmod.core.exception import DmodRuntimeError
from dmod.core.meta_data import DataCategory, DataFormat
from os import getenv
import docker
from docker.models.services import Service as DockerService
from docker.types import Mount, SecretReference
from docker.models.services import Service as DockerService
import yaml
from typing import Dict, List, Optional, TYPE_CHECKING, Tuple

## local imports
from .utils import parsing_nested as pn

# Imports strictly for type hinting
if TYPE_CHECKING:
    from .job import Job


class DockerServiceParameters():
    def __init__(self, image_tag: str = None, constraints: list = [], user: Optional[str] = None, hostname: str = None,
                 labels: dict = {}, serv_name: str = None, mounts: list = [], env_vars: Optional[Dict[str, str]] = None,
                 secrets: List[SecretReference] = [], cap_add: Optional[List[str]] = None):
        """
        Parameters
        ----------
        image_tag
            image parameter for client.services.create()
        constraints
            constraints parameter for client.services.create()
        user
            service user parameter for client.services.create()
        hostname
            hostname parameter for client.services.create()
        labels
            labels parameter for client.services.create()
        name
            name parameter for client.services.create()
        mounts
            mounts parameter for client.services.create()
        env_vars
            Optional map of environment variables to values (all as strings)
        secrets
            List of Docker ::class:`SecretReference` objects
        cap_add
            Optional list of kernel capabilities to add to the default set for the container, passed to
            client.services.create()
        """
        self.image_tag = image_tag
        self.constraints = constraints
        self.hostname = hostname
        self.labels = labels
        self.serv_name = serv_name
        self.mounts = mounts
        self.secrets = secrets
        self.env_var_map = env_vars
        self.user = user
        self.capabilities_to_add = cap_add

    @property
    def env_var_list(self) -> List[str]:
        """
        List of environment variables from ::attribute:`env_var_map` property, in the format ``KEY=value``.

        This is the format require when passing through the Docker SDK, but is not as intuitive as a dict/map.

        Returns
        -------
        List[str]
            List of environment variables from ::attribute:`env_var_map` property, in the format ``KEY=value``.
        """
        return ["{}={}".format(key, self.env_var_map[key]) for key in self.env_var_map]


class SimpleDockerUtil:
    """
    Simple class that can work with Docker.
    """
    def __init__(self, docker_client=None, api_client=None, **kwargs):
        """
        Parameters
        ----------
        docker_client
            Docker API client
        api_client
            Docker Low-level API client
        """
        if docker_client:
            self.docker_client = docker_client
            self.api_client = api_client
        else:
            self.checkDocker()
            self.docker_client = docker.from_env()
            self.api_client = docker.APIClient()

    def checkDocker(self):
        """Test that docker is up running"""
        try:
            # Check docker client state
            docker.from_env().ping()
        except:
            raise ConnectionError("Please check that the Docker Daemon is installed and running.")

    def get_secret_reference(self, secret_name: str):
        """
        Initialize and return a new ::class:`SecretReference` object for the Docker secret of the given name.

        Works by using the client API to obtain a ::class:`docker.models.Secret` object and using that to create and
        return a new ::class:`SecretReference`.

        Parameters
        ----------
        secret_name : str
            The name of the secret of interest

        Returns
        -------

        Raises
        -------
        ::class:`docker.errors.NotFound`
            If the secret does not exist.
        ::class:`docker.errors.APIError`
            If the server returns an error.
        """
        secret_obj = self.docker_client.secrets.get(secret_name)
        return SecretReference(secret_id=secret_obj.id, secret_name=secret_obj.name)

    def run_container(self, image: str, **kwargs):
        return self.docker_client.containers.run(image=image,
                                                 command=kwargs.pop('command', None),
                                                 stdout=kwargs.pop('stdout', True),
                                                 stderr=kwargs.pop('stderr', False),
                                                 remove=kwargs.pop('remove', False),
                                                 **kwargs)


class Launcher(SimpleDockerUtil):

    def __init__(self, images_and_domains_yaml, docker_client=None, api_client=None, **kwargs):
        """ FIXME
        Parameters
        ----------
        docker_client
            Docker API client
        api_client
            Docker Low-level API client
        """
        super(Launcher, self).__init__(docker_client, api_client, **kwargs)
        self._images_and_domains_yaml = images_and_domains_yaml

        #FIXME make networks, stack name __init__ params

        self.constraints = []
        self.hostname = "{{.Service.Name}}"

        #FIXME parameterize network
        self.networks = ["mpi-net"]

    def create_service(self, serviceParams: DockerServiceParameters, idx: int, docker_cmd_args: List[str]) \
        -> DockerService:
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

        # Put things that we aren't sure will show up into this
        additional_kwargs = dict()
        if len(serviceParams.secrets) > 0:
            additional_kwargs['secrets'] = serviceParams.secrets
        if serviceParams.env_var_map is not None and len(serviceParams.env_var_map) > 0:
            additional_kwargs['env'] = serviceParams.env_var_list
        if serviceParams.user is not None:
            additional_kwargs['user'] = serviceParams.user
        if serviceParams.capabilities_to_add is not None and len(serviceParams.capabilities_to_add) > 0:
            additional_kwargs['cap_add'] = serviceParams.capabilities_to_add

        healthcheck = docker.types.Healthcheck(test=["CMD-SHELL", 'echo Hello'],
                                               interval=1000000 * 10000 * 1,
                                               timeout=1000000 * 10000 * 2,
                                               retries=2,
                                               start_period=1000000 * 10000)
        # delay 5 minutes before restarting
        # restart = docker.types.RestartPolicy(condition='on-failure')
        restart = docker.types.RestartPolicy(condition='none')

        try:
            service = client.services.create(image=image,
                                             args=docker_cmd_args,
                                             constraints=constraints,
                                             hostname=hostname,
                                             labels=serv_labels,
                                             name=serv_name,
                                             mounts=mounts,
                                             networks=networks,
                                             healthcheck=healthcheck,
                                             restart_policy=restart,
                                             **additional_kwargs)
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

    @staticmethod
    def build_host_list(job: 'Job') -> str:
        """
        Build a comma-delimited string for the worker hosts argument to be passed when starting job Docker services.

        Build a "list" (as a comma-delimited string) of the MPI host strings that must be passed when starting the
        Docker worker node services for scheduling/executing a job.  These hosts strings each consist of that worker's
        Docker service name (which is usable on the Docker networks to resolve the worker container) and the number of
        CPUs for that worker.

        Parameters
        ----------
        job
            The related job object, which contains an iterable collection of the relevant allocations and analogous
            collection of corresponding service names for the invocations of such allocations.

        Returns
        -------
        str
            Container hosts argument string, in the format ``<host_name>:<num_cores>[,<host_name>:<num_cores>]*``.
        """
        num_allocations = len(job.allocations) if job.allocations is not None else 0
        host_strs = []

        if num_allocations > 0:
            for idx in range(num_allocations):
                host_strs.append('{}:{}'.format(job.allocation_service_names[idx], job.allocations[idx].cpu_count))

        return ','.join(host_strs)

    @classmethod
    def _ds_names_helper(cls, job: 'Job', worker_index: int, category: DataCategory,
                         data_format: Optional[DataFormat] = None, min_count: Optional[int] = 1,
                         max_count: Optional[int] = None) -> List[str]:
        """
        Get required dataset names of a category for a worker/allocation, and sanity check those are configured right.

        Parameters
        ----------
        job : Job
            The job of interest.
        worker_index : int
            Index of the worker and of the sublist of requirements in ::attribute:`Job.worker_data_requirements`.
        category : DataCategory
            The data requirement category type of interest.
        data_format : Optional[DataFormat]
            Optional data format restriction for applicable datasets.
        min_count : Optional[int]
            Optional minimum number of expected dataset names for this worker and category (default ``1``).
        max_count : Optional[int]
            Optional minimum number of expected dataset names for this worker and category (default: ``None``).

        Returns
        -------
        List[str]
            List of the names of datasets fulfilling all the data requirements of the given category for the specified
            job worker/allocation.
        """
        # First, filter to requirements of the specified working and category
        reqs_for_category = [req for req in job.worker_data_requirements[worker_index] if req.category == category]

        # If a format set (typically only for specialized config datasets), filter by that as well
        # Also, reduce the requirements to fulfilling dataset names
        if data_format is None:
            dataset_names = set([r.fulfilled_by for r in reqs_for_category])
        else:
            dataset_names = set([r.fulfilled_by for r in reqs_for_category if r.domain.data_format == data_format])

        # Sanity check the number of dataset names and that we know the fulfilling dataset for all requirements
        if min_count is not None and len(dataset_names) < min_count:
            msg = "Attempting to start {} job {} with fewer than allowed minimum of {} required {} datasets."
            raise RuntimeError(msg.format(job.model_request.__class__.__name__, job.job_id, min_count, category))
        elif max_count is not None and len(dataset_names) > max_count:
            msg = "Attempting to start {} job {} with more than allowed max of {} required {} datasets."
            raise RuntimeError(msg.format(job.model_request.__class__.__name__, job.job_id, max_count, category))
        elif None in dataset_names is None:
            msg = "Attempting to start {} job {} with unfulfilled {} data requirement."
            raise RuntimeError(msg.format(job.model_request.__class__.__name__, job.job_id, category))
        # If things look good, return the set of names we found after converting to a list
        else:
            return list(dataset_names)

    # TODO (later): once we get to dynamic/custom images (i.e., for arbitrary BMI modules), make sure this still works
    def _generate_docker_cmd_args(self, job: 'Job', worker_index: int) -> List[str]:
        """
        Create the Docker "CMD" arguments list to be used to start all services that will perform this job.

        Docker "CMD" arguments are the arguments that will be passed to the Docker entrypoint script/executable when
        starting a container.  This function essentially generates the appropriate arguments for the applicable
        entrypoint script, in order to start the worker service at the given index, among the collection of all worker
        services involved with executing the given job.

        Parameters
        ----------
        job : Job
            The job to have worker Docker services started, with those services needing "CMD" arguments generated.
        worker_index : int
            The particular worker service index in question, which will have a specific set of data requirements.

        Returns
        -------
        List[str]
            A list of the Docker "COMMAND" args to be used when creating the worker service at the given index.

        See Also
        -------
        https://docs.docker.com/engine/reference/builder/#cmd
        https://docs.docker.com/engine/reference/builder/#understand-how-cmd-and-entrypoint-interact
        """
        # TODO (later): handle non-model-exec jobs in the future
        if job.model_request.event_type != MessageEventType.MODEL_EXEC_REQUEST:
            raise RuntimeError("Unsupported requested job event type {}; cannot generate Docker CMD arg values".format(
                job.model_request.get_message_event_type()))

        # TODO (later): have something more intelligent than class type to determine right entrypoint format and
        #  values, but for now assume/require a "standard" image
        if not (isinstance(job.model_request, NWMRequest) or isinstance(job.model_request, NGENRequest)):
            raise RuntimeError("Unexpected request type {}: cannot build Docker CMD arg list".format(
                job.model_request.__class__.__name__))

        # For now at least, all image arg lists start the same way (first 3 args: node count, host string, and job id)
        # TODO: this probably should be a documented standard for any future entrypoints
        # TODO (later): probably need to move all types to recognize and use explicit flags rather than order arguments
        docker_cmd_args = [str(len(job.allocations)), self.build_host_list(job), job.job_id]

        if isinstance(job.model_request, NGENRequest):
            # $4 is the worker index (where index 0 is assumed to be the lead node)
            docker_cmd_args.append(str(worker_index))

            # $5 is the name of the output dataset (which will imply a directory location)
            output_dataset_names = self._ds_names_helper(job, worker_index, DataCategory.OUTPUT, max_count=1)
            docker_cmd_args.append(output_dataset_names[0])

            # $6 is the name of the hydrofabric dataset (which will imply a directory location)
            hydrofabric_dataset_names = self._ds_names_helper(job, worker_index, DataCategory.HYDROFABRIC, max_count=1)
            docker_cmd_args.append(hydrofabric_dataset_names[0])

            # $7 is the name of the realization configuration dataset (which will imply a directory location)
            realization_cfg_dataset_names = self._ds_names_helper(job, worker_index, DataCategory.CONFIG, max_count=1,
                                                                  data_format=DataFormat.NGEN_REALIZATION_CONFIG)
            docker_cmd_args.append(realization_cfg_dataset_names[0])

            # $8 is the name of the BMI config dataset (which will imply a directory location)
            bmi_config_dataset_names = self._ds_names_helper(job, worker_index, DataCategory.CONFIG, max_count=1,
                                                             data_format=DataFormat.BMI_CONFIG)
            docker_cmd_args.append(bmi_config_dataset_names[0])

            # $9 is the name of the partition config dataset (which will imply a directory location)
            # TODO: this probably will eventually break things if $10 is added for calibration config dataset
            # TODO: need to overhaul entrypoint for ngen and ngen-calibration images with flag-based args
            if job.cpu_count > 1:
                partition_config_dataset_names = self._ds_names_helper(job, worker_index, DataCategory.CONFIG,
                                                                       max_count=1,
                                                                       data_format=DataFormat.NGEN_PARTITION_CONFIG)
                docker_cmd_args.append(partition_config_dataset_names[0])

            # $10 is the name of the calibration config dataset (which will imply a directory location)
            # TODO: this *might* need to be added depending on how we decide to handle calibration
            # configs. meaning if they are datasets or not.
            # calibration_config_dataset_names = self._ds_names_helper(job, worker_index, DataCategory.CONFIG, max_count=1,
            #                                                     data_format=DataFormat.NGEN_CAL_CONFIG)
            # docker_cmd_args.append(calibration_config_dataset_names[0])

            # Also do a sanity check here to ensure there is at least one forcing dataset
            self._ds_names_helper(job, worker_index, DataCategory.FORCING)

        return docker_cmd_args

    def _get_required_obj_store_datasets_arg_strings(self, job: 'Job', worker_index: int) -> List[str]:
        """
        Get list of colon-joined category+name strings for required object store datasets for this job worker.

        Function first finds the collection of datasets that are stored in the object store and needed to fulfill one of
        the ::class:`DataRequirement` objects of the specified worker for the given job (i.e., as stored in the nested
        list at index ``worker_index`` of this job's ::attribute:`Job.worker_data_requirements` property).  It then maps
        each of these datasets to a string in the form <category_name>:<dataset_name> (e.g.,
        FORCING:aorc_csv_forcings_1).  This is the format required for the ``ngen`` entrypoint script to know what
        object store dataset buckets to mount in the file system.  The function then returns this map of strings.

        Parameters
        ----------
        job : Job
            The job for which there is need of the entrypoint string args for required object store datasets.
        worker_index : int
            The particular worker service index in question, which will have a specific set of data requirements.

        Returns
        -------
        List[str]
            The entrypoint string args for all required object store datasets for the referenced worker.
        """
        name_list = []
        for requirement in job.worker_data_requirements[worker_index]:
            if requirement.fulfilled_by is None:
                msg = "Can't get object store arg strings and start job {} with unfulfilled data requirements"
                raise RuntimeError(msg.format(str(job.job_id)))
            if self._is_object_store_dataset(dataset_name=requirement.fulfilled_by):
                name_list.append('{}:{}'.format(requirement.category.name.lower(), requirement.fulfilled_by))
        return name_list

    def _is_object_store_dataset(self, dataset_name: str):
        """
        Test whether the dataset of the given name is stored in the object store.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset of interest.

        Returns
        -------
        bool
            Whether the dataset of the given name is stored in the object store.
        """
        # TODO (later): for now, when only this type is supported, assume always true, but need to fix this
        return True

    def determine_image_for_job(self, job: 'Job') -> str:
        """
        Determine the correct Docker image to use for the given job.

        Parameters
        ----------
        job : Job
            The job of interest.

        Returns
        -------
        str
            String name, including tag, of the appropriate Docker image for this job.
        """
        if isinstance(job.model_request, NGENRequest):
            return "127.0.0.1:5000/ngen:latest"
        else:
            msg = "Unable to determine correct scheduler image for job {} with request of {} type"
            raise DmodRuntimeError(msg.format(job.job_id, job.model_request.__class__.__name__))

    # TODO: look at removing once a better way of handling image select is finished
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
            # Keys in model['version'] may not be strings, but the version parameter will be, so convert
            version_key = None
            for v_key_literal in model['version']:
                if str(v_key_literal) == version:
                    version_key = v_key_literal
                    break
            image = model['version'][version_key]
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

        if len([a for a in job.allocations if a.cpu_count <= 0]):
            msg = "Cannot start job {}; found allocation without positive CPU count"
            logging.error(msg)
            return False, tuple(msg)

        image_tag = self.determine_image_for_job(job)

        #TODO better align labels/defaults with serviceparam class
        #FIXME if the stack.namespace needs to align with the stack name, this isn't correct
        labels = {"com.docker.stack.image": image_tag, "com.docker.stack.namespace": model}

        #This seems to be more of a dev check than anything required
        #self.write_hostfile(basename, cpusList)
        num_allocations = len(job.allocations) if job.allocations is not None else 0
        if num_allocations == 0:
            logging.error("Attempting to start job {} that has no allocations".format(str(job.job_id)))
            return False, tuple()

        service_per_allocation = []

        # TODO: might want to adjust this in the future to be lazy in case not always needed
        # Get the Docker Secrets for object store data access
        # TODO (later): might need to expand to use different users for different situations (create JobType?)
        # Note that client gets docker.models.secrets.Secret objects, but service creation requires
        #   docker.types.SecretReference objects, so have to do a little manipulation
        secrets = [self.get_secret_reference(secret_name) for secret_name in
                   ['object_store_exec_user_name', 'object_store_exec_user_passwd']]

        for alloc_index in range(num_allocations):
            alloc = job.allocations[alloc_index]
            constraints_str = "node.hostname == {}".format(alloc.hostname)
            constraints = list(constraints_str.split("/"))

            pattern = '{}:/dmod/datasets/{}/{}:rw'
            mounts = [pattern.format(r.fulfilled_access_at, r.category.name.lower(), r.fulfilled_by) for r in
                      job.worker_data_requirements[alloc_index] if r.fulfilled_access_at is not None]
            #mounts.append('/local/model_as_a_service/docker_host_volumes/forcing_local:/dmod/datasets/forcing_local:rw')
            # Introduce a way to inject data access directly via env config, to potentially bypass things for testing
            bind_mount_from_env = getenv('DMOD_JOB_WORKER_HOST_MOUNT')
            if bind_mount_from_env is not None:
                mounts.append('{}:/dmod/datasets/from_env:rw'.format(bind_mount_from_env))

            logging.info("Hostname: {}".format(alloc.hostname))
            #FIXME important that all label values are strings, otherwise docker service create hangs
            labels_tmp = {"Hostname": alloc.hostname, "cpus_alloc": str(alloc.cpu_count)}
            labels.update(labels_tmp)

            serv_name = job.allocation_service_names[alloc_index]

            # Create the docker service
            service_params = DockerServiceParameters(image_tag=image_tag, constraints=constraints, labels=labels,
                                                     hostname=job.allocation_service_names[alloc_index],
                                                     serv_name=serv_name, mounts=mounts, secrets=secrets)
            if model == 'ngen':
                # For ngen jobs (at least for the moment), the container initially needs root as the user for sshd
                service_params.user = 'root'
                # Also adding this for ngen
                service_params.capabilities_to_add = ['SYS_ADMIN']
            #TODO check for proper service creation, return False if doesn't work
            service = self.create_service(serviceParams=service_params, idx=alloc_index,
                                          docker_cmd_args=self._generate_docker_cmd_args(job, alloc_index))
            service_per_allocation.append(service)

        logging.info("\n")
        return True, tuple(service_per_allocation)
