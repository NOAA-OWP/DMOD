import unittest
from pathlib import Path
from ..scheduler.scheduler import Launcher
from . import mock_job


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

        #Create a launcher TODO only test static methods here, no instance so no docker neeeded
        self.launcher = NoCheckDockerLauncher(images_and_domains_yaml=yaml_file)

    def tearDown(self) -> None:
        #This class should only test static methods and work without docker FIXME
        self.launcher.docker_client.close()

    def test_build_host_list(self):
        """
        Test build_host_list for a job with no allocation
        """
        job = mock_job(allocations=0)
        hosts = self.launcher.build_host_list(job)
        self.assertEqual(hosts, '')

    def test_build_host_list_1(self):
        """
        Test build_host_list for a job with a single node allocated
        """
        job = mock_job(allocations=1)
        hosts = self.launcher.build_host_list(job)
        self.assertEqual(hosts, 'nwm-worker0_{}:4'.format(job.job_id))

    def test_build_host_list_2(self):
        """
        Test build_host_list for a job with multiple nodes allocated
        """
        job = mock_job(allocations=2)
        hosts = self.launcher.build_host_list(job)
        self.assertEqual(hosts, 'nwm-worker0_{}:4,nwm-worker1_{}:4'.format(job.job_id, job.job_id))

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
