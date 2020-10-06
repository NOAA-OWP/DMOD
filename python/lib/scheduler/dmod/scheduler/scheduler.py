#!/usr/bin/env python3

import logging
from requests.exceptions import ReadTimeout
import docker
import yaml
from typing import TYPE_CHECKING

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

    def create_service(self, serviceParams: DockerServiceParameters, idx: int, args: list) \
        -> docker.from_env().services.create:
        """
        Create new service with Healthcheck, host, and other info

        Parameters
        ----------
        serviceParams
            A DockerServiceParameters class object
        idx
            Index number for labeling a Docker service name
        args
            list of args to pass to the service, including a string of hostnames and cpus_alloc for running MPI job

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
            args.append(str(idx))

        try:
            service = client.services.create(image = image,
                                         args = args,
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
    def build_host_list(basename: str, job: 'Job') -> str:
        """
        build a list of strings that contain the container names and the allocated CPUs on the associated hosts

        Parameters
        ----------
        basename
            Base name of a MPI worker service in an indexed collection of services
        job
            The related job object, which contains a list of the relevant allocations.

        Returns
        -------
        host_str: str
            string of newline seperated <host_name>:<num_cores> entries
        """
        host_str = ''

        idx = 0
        for allocation in job.allocations:
            cpus_alloc = str(allocation.cpu_count)
            #FIXME get nameing better orgainized across all functions
            name = basename + str(idx) + "_{}".format(job.job_id)
            host_tmp = name + ':' + cpus_alloc+'\n'
            host_str = host_str+host_tmp
            idx += 1
        #Strip any trailing newline
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

    def start_job(self, job: 'Job'):
        """

        """
        #TODO read these from request metadata
        model = job.originating_request.model_request.get_model_name()
        name = "{}-worker".format(model)
        #FIXME read all image/domain at init and select from internal cache (i.e. dict) or even push to redis for long term cache
        (image_tag, mounts) = self.load_image_and_mounts(model,
                                                         job.originating_request.model_request.version,
                                                         job.originating_request.model_request.domain)

        #TODO better align labels/defaults with serviceparam class
        #FIXME if the stack.namespace needs to align with the stack name, this isn't correct
        labels =  {"com.docker.stack.image": image_tag,
                   "com.docker.stack.namespace": model
                   }
        host_str = self.build_host_list(name, job, run_domain_dir)
        #This seems to be more of a dev check than anything required
        #self.write_hostfile(basename, cpusList)
        cpusLen = len(job.allocations)
        idx = 0
        for alloc in job.allocations:
            constraints = "node.hostname == "
            NodeId = alloc.pool_id
            #FIXME this is a local environment hard coded, needs removed
            if (NodeId == "Node-0001"):
                #mounts = ['/opt/nwm_c/domains:/nwm/domains:rw']
                mts_string = domain_dir + ':' + run_domain_dir + ':' + 'rw'
                mounts = [mts_string]
            else:
                mounts = ['/local:/nwm/domains:rw']
            cpus_alloc = alloc.cpu_count
            hostname = alloc.hostname
            logging.info("Hostname: {}".format(hostname))
            #FIXME important that all label values are strings, otherwise docker service create hangs
            labels_tmp = {"Hostname": hostname, "cpus_alloc": str(cpus_alloc)}
            labels.update(labels_tmp)
            constraints += hostname
            constraints = list(constraints.split("/"))
            #TODO review all self attributes
            serv_name = "{}{}_{}".format(name, idx, job.job_id)
            #Create the docker service
            serviceParams = DockerServiceParameters(image_tag, constraints, hostname, labels, serv_name, mounts)
            #TODO check for proper service creation, return False if doesn't work
            service = self.create_service(serviceParams, idx, args)
            idx += 1
        logging.info("\n")
        return (True, service)
