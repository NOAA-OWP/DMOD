import unittest
from pathlib import Path
from ..scheduler.job import RequestedJob
from ..scheduler.resources import ResourceAllocation
from ..scheduler.scheduler import Launcher
from dmod.core.meta_data import TimeRange
from dmod.communication import NGENRequest, SchedulerRequestMessage


class NoCheckDockerLauncher(Launcher):
    """
    Extension of Docker launcher class, strictly for unit testing, which overrides the implementation of the
    ::method:`Launcher.checkDocker` method to not perform check of the OS-level Docker application/service.
    """

    def __init__(self, images_and_domains_yaml, docker_client=None, api_client=None, **kwargs):
        super().__init__(images_and_domains_yaml=images_and_domains_yaml,
                         docker_client=docker_client,
                         api_client=api_client,
                         **kwargs)

    def checkDocker(self):
        """
        Override of superclass method to not actually perform check (i.e., when unit testing).
        """
        pass


class TestLauncher(unittest.TestCase):

    def setUp(self) -> None:
        yaml_file = Path(__file__).parent/"image_and_domain.yaml"
        self.user_name = 'test'

        self._example_jobs = []
        time_range = TimeRange.parse_from_string('2022-01-01 00:00:00 to 2022-03-01 00:00:00')
        cpu_count = 4
        mem_size = 5000
        example_request = NGENRequest.factory_init_from_deserialized_json({
            "allocation_paradigm": "SINGLE_NODE",
            "cpu_count": cpu_count,
            "job_type": "ngen",
            'request_body': {
                'bmi_config_data_id': '02468',
                'composite_config_data_id': 'composite02468',
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'realization_config_data_id': '02468',
                'time_range': time_range.to_dict()
            },
            'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        })
        user_id = 'user'

        # Example 0 - no allocations
        sch_req = SchedulerRequestMessage(model_request=example_request,
                                          user_id=user_id,
                                          cpus=cpu_count,
                                          mem=mem_size,
                                          allocation_paradigm='SINGLE_NODE')
        self._example_jobs.append(RequestedJob(sch_req))

        # Example 1 - with a single node allocated with 4 cpus
        sch_req = SchedulerRequestMessage(model_request=example_request,
                                          user_id=user_id,
                                          cpus=cpu_count,
                                          mem=mem_size,
                                          allocation_paradigm='SINGLE_NODE')
        ex_job = RequestedJob(sch_req)
        alloc = ResourceAllocation('1', 'hostname1', cpu_count, mem_size)
        ex_job.allocations = [alloc]
        self._example_jobs.append(ex_job)

        # Example 2 - with two node allocated with 4 cpus
        example_request_multi = NGENRequest.factory_init_from_deserialized_json({
            "allocation_paradigm": "SINGLE_NODE",
            "cpu_count": cpu_count,
            "job_type": "ngen",
            'request_body': {
                'bmi_config_data_id': '02468',
                'composite_config_data_id': 'composite02468',
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'realization_config_data_id': '02468',
                'time_range': time_range.to_dict()
            },
            'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        })
        user_id = 'user'
        sch_req = SchedulerRequestMessage(model_request=example_request_multi,
                                          user_id=user_id,
                                          cpus=cpu_count,
                                          mem=mem_size,
                                          allocation_paradigm='ROUND_ROBIN')
        ex_job = RequestedJob(sch_req)
        allocs = []
        allocs.append(ResourceAllocation('1', 'hostname1', 2, int(mem_size/2)))
        allocs.append(ResourceAllocation('2', 'hostname2', 2, int(mem_size/2)))
        ex_job.allocations = allocs
        self._example_jobs.append(ex_job)


        #Create a launcher TODO only test static methods here, no instance so no docker neeeded
        self.launcher = NoCheckDockerLauncher(images_and_domains_yaml=yaml_file)

    def tearDown(self) -> None:
        #This class should only test static methods and work without docker FIXME
        self.launcher.docker_client.close()

    def test_build_host_list_0(self):
        """
        Test build_host_list for a job with no allocation
        """
        ex_num = 0
        job = self._example_jobs[ex_num]
        hosts = self.launcher.build_host_list(job)
        self.assertEqual(hosts, '')

    def test_build_host_list_1(self):
        """
        Test build_host_list for a job with a single node allocated
        """
        ex_num = 1
        job = self._example_jobs[ex_num]
        hosts = self.launcher.build_host_list(job)
        self.assertEqual(hosts, 'ngen-worker0_{}:4'.format(job.job_id))

    def test_build_host_list_2(self):
        """
        Test build_host_list for a job with multiple nodes allocated
        """
        ex_num = 2
        job = self._example_jobs[ex_num]
        hosts = self.launcher.build_host_list(job)
        self.assertEqual(hosts, 'ngen-worker0_{}:2,ngen-worker1_{}:2'.format(job.job_id, job.job_id))

    def test_load_image_and_mounts(self):
        """
            Test load_image_and_mounts with empty string args
        """
        name = ''
        version = ''
        domain = ''
        with self.assertRaises(KeyError):
            self.launcher.load_image_and_mounts(name, version, domain)

    def test_load_image_and_mounts_a(self):
        """
            Test load_image_and_mounts with valid name, empty version and domain
        """
        name = 'nwm'
        version = ''
        domain = ''
        with self.assertRaises(KeyError):
            self.launcher.load_image_and_mounts(name, version, domain)

    def test_load_image_and_mounts_b(self):
        """
            Test load_image_and_mounts with empty name, valid version and domain
        """
        name = ''
        version = '2.0'
        domain = 'test-domain'
        with self.assertRaises(KeyError):
            self.launcher.load_image_and_mounts(name, version, domain)

    def test_load_image_and_mounts_c(self):
        """
            Test load_image_and_mounts with valid name, valid version and empty domain
        """
        name = 'nwm'
        version = '2.0'
        domain = ''
        with self.assertRaises(KeyError):
            self.launcher.load_image_and_mounts(name, version, domain)

    def test_load_image_and_mounts_1(self):
        """
            Test load_image_and_mounts with valid name, valid version, valid domain
        """
        name = 'nwm'
        version = '2.0'
        domain = 'croton_NY'
        image_tag, mounts = self.launcher.load_image_and_mounts(name, version, domain)

        self.assertIsNotNone(image_tag)
        self.assertIsNotNone(mounts)
        self.assertIsNotNone(mounts[0])
        self.assertIsNotNone(mounts[1])
        self.assertEqual(image_tag, '127.0.0.1:5000/nwm-2.0:latest')
        self.assertEqual( mounts[0], './domains:./example_case/NWM:rw')
        self.assertEqual( mounts[1], './local_out:/run_out:rw')
