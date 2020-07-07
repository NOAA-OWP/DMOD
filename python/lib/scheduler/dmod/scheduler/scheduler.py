#!/usr/bin/env python3

import logging
from requests.exceptions import ReadTimeout
import docker
import yaml
from typing import TYPE_CHECKING
from .utils import parsing_nested as pn

# Imports strictly for type hinting
if TYPE_CHECKING:
    from .job import Job

logging.basicConfig(
    filename='scheduler.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")


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
        redis
            Redis API
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
        #FIXME shouldn't have default nwm image if scheudler is generic

        ## initialize variables for create_service()
        ## default image
        self._default_image = "127.0.0.1:5000/nwm-2.0:latest"
        ## self.image =  "127.0.0.1:5000/nwm-master:latest"

        self.constraints = []
        self.hostname = "{{.Service.Name}}"
        #FIXME set label based on image_and_domain.yaml
        self.labels =  {"com.docker.stack.image": "127.0.0.1:5000/nwm-2.0",
                        "com.docker.stack.namespace": "nwm"
                       }
        #FIXME set name from model conf (images and domains)
        self.name = "nwm_mpi-worker_serv"
        #FIXME parameterize network
        self.networks = ["mpi-net"]

    def create_service(self, serviceParams: DockerServiceParameters, idx: int, cpusLen: int, host_str: str) \
        -> docker.from_env().services.create:
        """
        Create new service with Healthcheck, host, and other info

        Parameters
        ----------
        serviceParams
            A DockerServiceParameters class object
        idx
            Index number for labeling a Docker service name
        cpusLen
            Length of the cpusList
        host_str
            Strings of hostnames and cpus_alloc for running MPI job

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

        args = host_str
        Healthcheck = docker.types.Healthcheck(test = ["CMD-SHELL", 'echo Hello'],
                                               interval = 1000000 * 10000 * 1,
                                               timeout = 1000000 * 10000 * 2,
                                               retries = 2,
                                               start_period = 1000000 * 10000)
        # delay 5 minutes before restarting
        # restart = docker.types.RestartPolicy(condition='on-failure')
        restart = docker.types.RestartPolicy(condition='none')
        if (idx == 0):
            service = client.services.create(image = image,
                                         # command = ['sh', '-c', 'sudo /usr/sbin/sshd -D'],
                                         command = ['/nwm/run_model.sh'],
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
        else:
            args = host_str
            try:
                service = client.services.create(image = image,
                                             # command = ['sh', '-c', 'sudo /usr/sbin/sshd -D'],
                                             command = ['/nwm/run_model.sh'],
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
        srv_basename = self.name
        self.log_service(self.name, service.id)

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

    def build_host_list(self, basename: str, job: 'Job', run_domain_dir: str) -> list:
        """
        build a list of strings that contain the container names and the allocated CPUs on the associated hosts

        Parameters
        ----------
        basename
            Base name of a MPI worker service in an indexed collection of services
        job
            The related job object, which contains a list of the relevant allocations.
        run_domain_dir
            Domain directory in the Docker service container where the job is to be run, this info is needed
            for automatic service expansion

        Returns
        -------
        host_str
            List of string containing number of hosts, hostname and CPUs allocation, and run domain directory
        """
        # Start list, and add the string for number of hosts
        num_hosts = str(len(job.allocations))
        host_str = [num_hosts]

        # Next, build an temporary allocations list
        allocation_str_list = []
        idx = 0
        for allocation in job.allocations:
            cpus_alloc = str(allocation.cpu_count)
            #FIXME get nameing better orgainized across all functions
            name = basename + str(idx) + "_{}".format(job.job_id)
            host_tmp = name + ':' + cpus_alloc
            allocation_str_list.append(str(host_tmp))
            idx += 1

        # Then reverse and add the allocations list to our returned list
        allocation_str_list.reverse()
        for e in allocation_str_list:
            host_str.append(e)

        # Finally, append the domain dir
        host_str.append(str(run_domain_dir))

        print("host_str", host_str)
        return host_str

    def load_image_and_domain(self, image_name: str, domain_name: str) -> tuple:
        """
        Read a list of image_name and domain_name from the yaml file: image_and_domain.yaml
        Derive domain directory to be used for computing
        The image_name needed and user requested domain_name must be in the list for a valid job request,
        otherwise, it is not supported

        Parameters
        ----------
        image_name
            The image name needed to run a user job
        domain_name
            The domain name as requested by a user

        Returns
        -------
        selected_image
            The selected image out of the valid image list in the yaml file, there is a match
        selected_domain_dir
            The selected domain directory out of the valid domain name : domain directory dicts in the yaml file
        run_domain_dir
            The run domain directory in the docker container, based on the domain name to directory mapping in the yaml file
        """

        # Load the yaml file into dictionary
        with open(self._images_and_domains_yaml) as fn:
            yml_obj = yaml.safe_load(fn)

        # key_list = {'domain_croton_NY':'domain_croton_NY',
        #             'domain_SixMileCreek': 'domain_SixMileCreek'
        #            }

        selected_domain_dir = None
        domain_name_list = yml_obj['nwm_domain_list']
        for item in domain_name_list:
            for key in item:
                # print(item[key])
                if (key == domain_name):
                    selected_domain_dir = item[key]
                    print("selected domain_name, domain dir: ", key, selected_domain_dir)

        # If requested domain does not exist on local machine
        if (selected_domain_dir == None):
            raise ValueError("domain-name: The requested domain is not a valid domain")

        # Set up the domain to run jobs on the container
        run_domain_dir = None
        domain_name_list = yml_obj['run_domain_list']
        for item in domain_name_list:
            for key in item:
                # print(item[key])
                if (key == domain_name):
                    run_domain_dir = item[key]
                    print("run_domain_name, run_domain dir: ", key, run_domain_dir)

        # If requested domain does not exist on local machine
        if (run_domain_dir == None):
            raise Exception("Failed to set up the run domain on the container")

        # Selecting the image that corresponds to user job request
        # If needed, different "image_tag" list can be created in image_and_domain_yaml file for different models,
        # then the following code can be run for each image_tag names
        # The code also ensure the required image exists on the system
        # selected_image = image_name
        image_tag_list = yml_obj['nwm_image_tag']
        selected_image = None
        for i, image_tag in enumerate(image_tag_list):
            # print("image_tag: ", image_tag)
            if (image_tag == image_name):
                selected_image = image_tag
                print("selected image = ", image_tag)
                break

        # If requested domain does not exist on local machine
        if (selected_image == None):
            raise ValueError("image_name: The requested image is not a valid image")

        return selected_image, selected_domain_dir, run_domain_dir

    def start_job(self, job: 'Job'):
        """

        """
        #TODO read these from request metadata
        #domain = job.originating_request.model_request.domain
        #image = map_image(job.origination_request.model_request.name, version)
        # In operation, domain_name will be taken from user request
        domain_name = "domain_croton_NY"
        image_name = "127.0.0.1:5000/nwm-master:latest"
        # Image is related to the domain type. For hydrologicla model, such as domain_croton_NY, we use nwm
        # image_name  = "127.0.0.1:5000/nwm-2.0:latest"
        # userRequest = Request(user_id, cpus, mem)
        #FIXME read all image/domain at init and select from internal cache (i.e. dict) or even push to redis for long term cache
        (image_tag, domain_dir, run_domain_dir) = self.load_image_and_domain(image_name, domain_name)
        #TODO better align labels/defaults with serviceparam class
        labels =  {"com.docker.stack.image": image_tag,
                   "com.docker.stack.namespace": "nwm"
                   }
        basename = self.name
        host_str = self.build_host_list(basename, job, run_domain_dir)
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
            serv_name = self.name + str(idx)+"_{}".format(job.job_id)
            idx += 1
            #Create the docker service
            serviceParams = DockerServiceParameters(image_tag, constraints, hostname, labels, serv_name, mounts)
            #TODO check for proper service creation, return False if doesn't work
            self.create_service(serviceParams, idx, cpusLen, host_str)
        logging.info("\n")
        return True
