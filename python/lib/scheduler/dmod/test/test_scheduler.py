import unittest
from pathlib import Path
from ..scheduler.scheduler import Launcher
from . import mock_job

class TestLauncher(unittest.TestCase):

    def setUp(self) -> None:
        yaml_file = Path(__file__).parent/"image_and_domain.yaml"
        self.user_name = 'test'

        #Create a launcher TODO only test static methods here, no instance so no docker neeeded
        self.launcher = Launcher(images_and_domains_yaml=yaml_file)

    def tearDown(self) -> None:
        #This class should only test static methods and work without docker FIXME
        self.launcher.docker_client.close()

    def test_build_host_list(self):
        """
        Test build_host_list for a job with no allocation
        """
        job = mock_job(allocations=0)
        hosts = self.launcher.build_host_list('fake-service', job, '/dev/null')
        self.assertEqual(2, len(hosts))
        self.assertEqual(hosts[0], '0')
        self.assertEqual(hosts[1], '/dev/null')

    def test_build_host_list_1(self):
        """
        Test build_host_list for a job with a single node allocated
        """
        job = mock_job(allocations=1)
        hosts = self.launcher.build_host_list('fake-service', job, '/dev/null')
        self.assertEqual(3, len(hosts))
        self.assertEqual(hosts[0], '1')
        self.assertEqual(hosts[1], 'fake-service0_{}:4'.format(job.job_id))
        self.assertEqual(hosts[2], '/dev/null')

    def test_build_host_list_2(self):
        """
        Test build_host_list for a job with multiple nodes allocated
        """
        job = mock_job(allocations=2)
        hosts = self.launcher.build_host_list('fake-service', job, '/dev/null')
        self.assertEqual(4, len(hosts))
        self.assertEqual(hosts[0], '2')
        self.assertEqual(hosts[1], 'fake-service1_{}:4'.format(job.job_id))
        self.assertEqual(hosts[2], 'fake-service0_{}:4'.format(job.job_id))
        self.assertEqual(hosts[3], '/dev/null')

    def test_load_image_and_domain(self):
        """
            Test load_image_and_domain with empty string args
        """
        image = ''
        domain = ''
        with self.assertRaises(ValueError):
            self.launcher.load_image_and_domain(image, domain)

    def test_load_image_and_domain_a(self):
        """
            Test load_image_and_domain with valid image, empty domain
        """
        image = '127.0.0.1:5000/nwm-2.0:latest'
        domain = ''
        with self.assertRaises(ValueError):
            self.launcher.load_image_and_domain(image, domain)

    def test_load_image_and_domain_b(self):
        """
            Test load_image_and_domain with empty image, valid domain
        """
        image = ''
        domain = 'domain_croton_NY'
        with self.assertRaises(ValueError):
            self.launcher.load_image_and_domain(image, domain)

    def test_load_image_and_domain_1(self):
        """
            Test load_image_and_domain with valid image, valid domain
        """
        image = '127.0.0.1:5000/nwm-2.0:latest'
        domain = 'domain_croton_NY'
        image_tag, static_dir, run_dir = self.launcher.load_image_and_domain(image, domain)

        self.assertIsNotNone(image, image_tag)
        self.assertIsNotNone(static_dir)
        self.assertIsNotNone(run_dir)
        self.assertEqual(image_tag, image)
        self.assertEqual( static_dir, './domains')
        self.assertEqual(run_dir, './example_case/NWM')
