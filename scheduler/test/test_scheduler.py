import unittest
import inspect

from scheduler.scheduler import Scheduler
from scheduler.scheduler import check_for_incoming_req
import scheduler.utils.keynamehelper as keynamehelper
from scheduler.request import Request
import scheduler.parsing_nested as pn

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

# from scheduler.request import Request
# from scheduler.utils import keynamehelper
# from scheduler.imports import generate, parsing_nested
redis = None

class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = Scheduler()
        user_id = "shengting.cui"
        cpus = 5
        mem = 5000000000
        self.request = Request(user_id, cpus, mem)
 
    def test_1(self):
        returnValue = check_for_incoming_req()
        self.assertEqual(returnValue, 1)

    def test_2_create_resources(self):
        e_set_key = keynamehelper.create_key_name("resources")
        self.assertTrue(isinstance(e_set_key, str))
        for resource in resources:
            e_key = keynamehelper.create_key_name("resource", resource['node_id'])
            self.assertTrue(isinstance(e_key, str))
            self.assertTrue((self.scheduler.redis.hmset(e_key, resource) is not None))
            self.assertTrue((self.scheduler.redis.sadd(e_set_key, resource['node_id']) is not None))

    def test_3_create_user_from_username(self):
        user_id = "shengting.cui"
        try:
            c_key = keynamehelper.create_key_name("user", user_id)
            user = {'user_id': user_id}
            self.assertTrue((self.scheduler.redis.hmset(c_key, user) is not None))
        except:
            # use assertLogs(logger)
            print("create user exception: user not created")
        
    """
    def test_4_check_single_node_availability(self):
        returnValue = self.scheduler.check_single_node_availability("shengting.cui", 25, 5000000000)
        self.assertTrue(isinstance(returnValue, list))

    def test_5_check_generalized_round_robin(self):
        returnValue = self.scheduler.check_generalized_round_robin("shengting.cui", 5, 5000000000)
        self.assertTrue(isinstance(returnValue, list))

    def test_6_check_availability_and_schedule(self):
        returnValue = self.scheduler.check_availability_and_schedule("shengting.cui", 150, 5000000000)
        self.assertTrue(isinstance(returnValue, list))
    """

    def test_7_print_resource_details(self):
        print("")
        for resource in resources:
            e_key = keynamehelper.create_key_name("resource", resource['node_id'])
            self.assertTrue(isinstance(e_key, str))
            # need to use assertLogs(logger)
            # logging.info("hgetall(e_key): {}".format(self.scheduler.redis.hgetall(e_key)))
            print("hgetall(e_key): {}".format(self.scheduler.redis.hgetall(e_key)))

    def test_8_service_to_host_mapping(self):
        self.assertTrue(self.scheduler.docker_client is not None)
        self.assertTrue(self.scheduler.api_client is not None)

    def test_9_create_service(self):
        pass

    def test_10_update_service(self):
        pass

    def test_11_checkDocker(self):
        self.assertTrue(self.scheduler.docker_client.ping())

    '''
    # Nested inner function should not be called in actual test
    # the fromRequest() function change the value of _jobQ used in startJobs()
    def test_12_fromRequest(self):
        user_id = "shengting.cui"
        cpus = 5
        mem = 5000000000
        returnClass = self.scheduler.fromRequest(user_id, cpus, mem, 0)
        print("")
        print("type of returnClass:", type(returnClass))
        r_val = type(returnClass)
        self.assertTrue(inspect.isclass(r_val))
    '''

    """
    def test_13_runJob(self):
    # def runJob(self, request, image, constraints, hostname, serv_labels, serv_name, cpus_alloc, mounts, networks, idx, cpusLen, host_str):
        user_id = "shengting.cui"
        cpus = 5
        mem = 5000000000
        # cpusList = self.scheduler.check_single_node_availability(user_id, cpus, mem)
        # cpusList = self.scheduler.check_generalized_round_robin(user_id, cpus, mem)
        cpus = 150
        cpusList = self.scheduler.check_availability_and_schedule(user_id, cpus, mem)
        basename = "nwm_mpi-worker_tmp"
        host_str = self.scheduler.build_host_list(basename, cpusList)

        # initialize variables for create_service()
        image = "127.0.0.1:5000/nwm-2.0:latest"
        constraints = []
        hostname = "{{.Service.Name}}"
        labels =  {"com.docker.stack.image": "127.0.0.1:5000/nwm-2.0",
                   "com.docker.stack.namespace": "nwm"
                  }
        # networks = ["mpi-net", "back40"]
        networks = ["mpi-net"]

        request = self.request
        idx = 0
        cpusLen = len(cpusList)
        for cpu in cpusList:
            constraints = "node.hostname == "
            NodeId = cpu['node_id']
            if (NodeId == "Node-0001"):
                mounts = ['/opt/nwm_c/domains:/nwm/domains:rw']
            else:
                mounts = ['/local:/nwm/domains:rw']
            cpus_alloc = str(cpu['cpus_alloc'])
            # print("In test_scheduler, cpus_alloc = {}".format(cpus_alloc))
            Hostname = cpu['Hostname']
            # logging.info("Hostname: {}".format(Hostname))
            labels_tmp = {"Hostname": Hostname, "cpus_alloc": cpus_alloc}
            labels.update(labels_tmp)
            # logging.info("labels: {}".format(labels))
            constraints += Hostname
            constraints = list(constraints.split("/"))
            # logging.info("constraints: {}".format(constraints))
            name = basename + str(idx)
            idx += 1
            schedule = self.scheduler.fromRequest(user_id, cpus_alloc, mem, idx)
            # This call directly creates three services: nwm_mpi-worker_tmp0, nwm_mpi-worker_tmp1, nwm_mpi-worker_tmp2
            service = schedule.runJob(request, image, constraints, hostname, labels, name, cpus_alloc, mounts, networks, idx, cpusLen, host_str)
        self.assertTrue(service is not None)
    """

    def test_14_startJobs(self):
        # startJobs(self, user_id, cpus, mem, image, constraints, hostname, serv_labels, serv_name, cpus_alloc, mounts, networks, idx, cpusLen, host_str)
        user_id = "shengting.cui"
        # cpus = 10
        mem = 5000000000
        # cpusList = self.scheduler.check_single_node_availability(user_id, cpus, mem)
        # cpus = 10
        # cpusList = self.scheduler.check_generalized_round_robin(user_id, cpus, mem)
        cpus = 221
        cpusList = self.scheduler.check_availability_and_schedule(user_id, cpus, mem)
        # cpus = 100
        # cpusList = self.scheduler.check_generalized_round_robin(user_id, cpus, mem)
        basename = "nwm_mpi-worker_tmp"
        host_str = self.scheduler.build_host_list(basename, cpusList)

        # initialize variables for create_service()
        image = "127.0.0.1:5000/nwm-2.0:latest"
        constraints = []
        hostname = "{{.Service.Name}}"
        labels =  {"com.docker.stack.image": "127.0.0.1:5000/nwm-2.0",
                   "com.docker.stack.namespace": "nwm"
                  }
        name = "nwm_mpi-worker_tmp"
        # networks = ["mpi-net", "back40"]
        networks = ["mpi-net"]

        # request = self.request
        idx = 0
        cpusLen = len(cpusList)
        print("cpusLen = ", cpusLen, "\n")
        for cpu in cpusList:
            name = "nwm_mpi-worker_tmp"
            constraints = "node.hostname == "
            NodeId = cpu['node_id']
            if (NodeId == "Node-0001"):
                mounts = ['/opt/nwm_c/domains:/nwm/domains:rw']
            else:
                mounts = ['/local:/nwm/domains:rw']
            cpus_alloc = str(cpu['cpus_alloc'])
            # print("In test_scheduler, cpus_alloc = {}".format(cpus_alloc))
            Hostname = cpu['Hostname']
            # logging.info("Hostname: {}".format(Hostname))
            labels_tmp = {"Hostname": Hostname, "cpus_alloc": cpus_alloc}
            labels.update(labels_tmp)
            # logging.info("labels: {}".format(labels))
            constraints += Hostname
            constraints = list(constraints.split("/"))
            # logging.info("constraints: {}".format(constraints))
            # name = basename + str(idx)
            name += str(idx)
            idx += 1
            schedule = self.scheduler.fromRequest(user_id, cpus_alloc, mem, idx)
            # This call directly creates three services: nwm_mpi-worker_tmp0, nwm_mpi-worker_tmp1, nwm_mpi-worker_tmp2
            len_jobQ = len(self.scheduler._jobQ)
            print("before calling startJobs(), len_jobQ = ", len_jobQ)
            schedule.startJobs(user_id, cpus, mem, image, constraints, hostname, labels, name, cpus_alloc, mounts, networks, idx, cpusLen, host_str)
            len_jobQ = len(self.scheduler._jobQ)
            print("after calling startJobs(), len_jobQ = ", len_jobQ, "\n")

    # nested inner function should not be called in actual test
    # The enqueue() function does not change the value of _jobQ used in startJobs()
    def test_15_enqueue(self):
        request = self.request
        len_jobQ = len(self.scheduler.__class__._jobQ)
        print("")
        print("before calling enqueue(), len_jobQ = ", len_jobQ)
        self.scheduler.enqueue(request)
        len_jobQ = len(self.scheduler.__class__._jobQ)
        print("after calling enqueue(), len_jobQ = ", len_jobQ, "\n")
        # print("_jobQ: ", self.scheduler.__class__._jobQ)
        # type_jobQ = type(self.scheduler.__class__._jobQ)
        # self.assertTrue(inspect.isfunction(type_jobQ))

    '''
    def test_16_build_host_list(self):
        user_id = "shengting.cui"
        cpus = 5
        mem = 5000000000
        # cpusList = self.scheduler.check_generalized_round_robin(user_id, cpus, mem)
        # cpusList = self.scheduler.check_single_node_availability(user_id, cpus, mem)
        # cpusList = self.scheduler.check_generalized_round_robin(user_id, cpus, mem)
        cpus = 150
        cpusList = self.scheduler.check_availability_and_schedule(user_id, cpus, mem)
        basename = "nwm_mpi-worker_tmp"
        return_strList = self.scheduler.build_host_list(basename, cpusList)
        self.assertTrue(isinstance(return_strList, list))
        print("return_strList: ", return_strList)
    '''

    def test_17_check_jobQ(self):
        que = self.scheduler._jobQ
        print("")
        print("job queue length = ", len(que))
        for job in que:
            print("In check_jobQ: user_id, cpus, mem: {} {} {}".format(job.user_id, job.cpus, job.mem))

    '''
    def test_18_check_runningJobs(self):
        client = self.scheduler.docker_client
        api_client = self.scheduler.api_client
        service_list = client.services.list()
        my_serviceLen = 0
        for service in service_list:
            # service_id may be useful later on
            service_id = service.id
            service_attrs = service.attrs
            Name = list(pn.find('Name', service_attrs))[0]
            if 'nwm_mpi-worker_tmp' in Name:
                my_serviceLen += 1

        user_id = "shengting.cui"
        cpus = 5
        mem = 5000000000
        # cpusList = self.scheduler.check_generalized_round_robin(user_id, cpus, mem)
        # cpusList = self.scheduler.check_single_node_availability(user_id, cpus, mem)
        # cpusList = self.scheduler.check_generalized_round_robin(user_id, cpus, mem)
        cpus = 150
        cpusList = self.scheduler.check_availability_and_schedule(user_id, cpus, mem)
        len_cpusList = len(cpusList)
        self.assertEqual(my_serviceLen, len_cpusList)
    '''

    # def test_19_clean_redisKeys(self):
        # self.scheduler.clean_redisKeys()

    def test_20_retrieve_job_metadata(self):
        user_id = "shengting.cui"
        print("")
        cpusList = self.scheduler.retrieve_job_metadata(user_id)
        self.assertTrue(isinstance(cpusList, list))
        print("-" * 5)
        print("return_cpusList: ", cpusList)


if __name__ == '__main__':
    unittest.main()
