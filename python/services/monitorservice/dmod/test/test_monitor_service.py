import unittest
import uuid
from typing import List, Optional, Tuple, Dict

from ..monitorservice.service import Monitor, MonitorService, Job, JobStatus, MetadataMessage, MetadataPurpose,\
    MonitoredChange
from dmod.scheduler.job import JobAllocationParadigm, JobImpl, JobExecStep


class MockEmptyMonitor(Monitor):

    def get_jobs_to_monitor(self) -> List[Job]:
        return []

    def monitor_jobs(self) -> Tuple[Dict[str, Job], Dict[str, JobStatus], Dict[str, JobStatus]]:
        return {}, {}, {}


class MockMonitorService(MonitorService):

    def __init__(self, monitor):
        super().__init__(monitor=monitor)
        self.connections = {}

    async def communicate_change(self, change: MonitoredChange):
        pass

    def get_connection_object(self, connection_id: str):
        return self.connections[connection_id] if connection_id in self.connections else None

    def register_connection(self, connection, jobs_of_interest: Optional[List[str]]) -> str:
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = connection
        self.jobs_of_interest_by_connection[connection_id] = jobs_of_interest if jobs_of_interest else None
        return connection_id


class TestJobImpl(unittest.TestCase):

    def setUp(self) -> None:
        self._services = []
        # First one has no actual monitor
        self._services.append(MockMonitorService(MockEmptyMonitor()))

        self._jobs = []
        self._jobs.append(JobImpl(cpu_count=4, memory_size=1000, model_request=None,
                                  allocation_paradigm=JobAllocationParadigm.SINGLE_NODE))

        self._connect_metadata_examples = []
        # Good, no interest list
        self._connect_metadata_examples.append('{"purpose": "CONNECT", "additional_metadata": false}')
        meta_example_2 = '{"purpose": "CONNECT", '
        meta_example_2 += '"config_changes": {"' + MonitorService.get_jobs_of_interest_config_key() + '": '
        meta_example_2 += '["52204a2f-8924-48b4-abab-d289ac5aedf7"]}, '
        meta_example_2 += '"additional_metadata": false}'
        self._connect_metadata_examples.append(meta_example_2)
        self._connect_metadata_examples.append('{"additional_metadata": false}')
        self._connect_metadata_examples.append('{"purpose": "PROMPT", "additional_metadata": false}')
        self._connect_metadata_examples.append('{"purpose": "CONNECT", "additional_metadata": true}')

        for j in self._jobs:
            j.status = JobStatus.MODEL_EXEC_AWAITING_ALLOCATION

    def tearDown(self) -> None:
        pass

    # Test object type for simple example change example for job
    def test__generate_update_msg_1_a(self):
        connection_id = str(uuid.uuid4())
        job = self._jobs[0]
        original_status = job.status
        job.status_step = JobExecStep.ALLOCATED
        change = MonitoredChange(job=job, original_status=original_status, connection_id=connection_id)

        update = MonitorService._generate_update_msg(change)
        self.assertEquals(change.job.__class__, update.object_type)

    # Test object id for simple example change example for job
    def test__generate_update_msg_1_b(self):
        connection_id = str(uuid.uuid4())
        job = self._jobs[0]
        original_status = job.status
        job.status_step = JobExecStep.ALLOCATED
        change = MonitoredChange(job=job, original_status=original_status, connection_id=connection_id)

        update = MonitorService._generate_update_msg(change)
        self.assertEquals(change.job.job_id, update.object_id)

    # Test correct key in update data for simple example change example for job
    def test__generate_update_msg_1_c(self):
        connection_id = str(uuid.uuid4())
        job = self._jobs[0]
        original_status = job.status
        job.status_step = JobExecStep.ALLOCATED
        change = MonitoredChange(job=job, original_status=original_status, connection_id=connection_id)

        update = MonitorService._generate_update_msg(change)
        self.assertTrue('status' in update.updated_data)

    # Test correct value in update data for simple example change example for job
    def test__generate_update_msg_1_d(self):
        connection_id = str(uuid.uuid4())
        job = self._jobs[0]
        original_status = job.status
        job.status_step = JobExecStep.ALLOCATED
        change = MonitoredChange(job=job, original_status=original_status, connection_id=connection_id)

        update = MonitorService._generate_update_msg(change)
        self.assertEquals(update.updated_data['status'], str(change.job.status))

    # Test that initially, by default, no jobs are of interest
    def test__is_connection_interested_1_a(self):
        ex_index = 0
        service = self._services[ex_index]

        connection_id = str(uuid.uuid4())

        self.assertFalse(connection_id in service.jobs_of_interest_by_connection)

        for i in range(0, 4):
            job_id = str(uuid.uuid4())
            self.assertFalse(service._is_connection_interested(connection_id, job_id))

    # Test after registering, with None set, all jobs are of interest
    def test__is_connection_interested_1_b(self):
        ex_index = 0
        service = self._services[ex_index]

        connection_id = service.register_connection(connection=self, jobs_of_interest=None)

        self.assertIsNone(service.jobs_of_interest_by_connection[connection_id])

        for i in range(0, 4):
            made_up_job_id = str(uuid.uuid4())
            self.assertTrue(service._is_connection_interested(connection_id, made_up_job_id))

    # Test after registering, with specific set (job is first and only), that job is of interest
    def test__is_connection_interested_1_c(self):
        ex_index = 0
        service = self._services[ex_index]

        random_job_id = '52204a2f-8924-48b4-abab-d289ac5aedf7'
        interest_list = []
        interest_list.append(random_job_id)

        connection_id = service.register_connection(connection=self, jobs_of_interest=interest_list)

        self.assertIsNotNone(service.jobs_of_interest_by_connection[connection_id])
        self.assertTrue(random_job_id in service.jobs_of_interest_by_connection[connection_id])
        self.assertTrue(service._is_connection_interested(connection_id, random_job_id))

    # Test after registering, with specific set (job is neither first nor only), that job is of interest
    def test__is_connection_interested_1_d(self):
        ex_index = 0
        service = self._services[ex_index]

        random_job_id = '52204a2f-8924-48b4-abab-d289ac5aedf7'
        interest_list = []
        for i in range(0, 4):
            interest_list.append(str(uuid.uuid4()))
        interest_list.append(random_job_id)

        connection_id = service.register_connection(connection=self, jobs_of_interest=interest_list)

        self.assertIsNotNone(service.jobs_of_interest_by_connection[connection_id])
        self.assertTrue(random_job_id in service.jobs_of_interest_by_connection[connection_id])
        self.assertTrue(service._is_connection_interested(connection_id, random_job_id))

    # Test after registering, with specific set, random other job ids are not of interest
    def test__is_connection_interested_1_e(self):
        ex_index = 0
        service = self._services[ex_index]

        random_job_id = '52204a2f-8924-48b4-abab-d289ac5aedf7'
        interest_list = []
        interest_list.append(random_job_id)

        connection_id = service.register_connection(connection=self, jobs_of_interest=interest_list)
        self.assertIsNotNone(service.jobs_of_interest_by_connection[connection_id])
        for i in range(0, 4):
            made_up_job_id = str(uuid.uuid4())
            self.assertFalse(made_up_job_id in service.jobs_of_interest_by_connection[connection_id])
            self.assertFalse(service._is_connection_interested(connection_id, made_up_job_id))

    # Test with valid case with no interest list metadata is not none
    def test__proc_connect_json_1_a(self):
        ex_index = 0
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertIsInstance(metadata, MetadataMessage)

    # Test with valid case with no interest list that success is true
    def test__proc_connect_json_1_b(self):
        ex_index = 0
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertTrue(success)

    # Test with valid case with no interest list metadata has right purpose
    def test__proc_connect_json_1_c(self):
        ex_index = 0
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertEqual(metadata.purpose, MetadataPurpose.CONNECT)

    # Test with valid case with no interest list metadata has right metadata_follows
    def test__proc_connect_json_1_d(self):
        ex_index = 0
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertFalse(metadata.metadata_follows)

    # Test with valid case with no interest list metadata has expected config_changes of None
    def test__proc_connect_json_1_e(self):
        ex_index = 0
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertIsNone(metadata.config_changes)

    # Test with valid case with interest list metadata is not none
    def test__proc_connect_json_2_a(self):
        ex_index = 1
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertIsInstance(metadata, MetadataMessage)

    # Test with valid case with interest list that success is true
    def test__proc_connect_json_2_b(self):
        ex_index = 1
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertTrue(success)

    # Test with valid case with interest list metadata has right purpose
    def test__proc_connect_json_2_c(self):
        ex_index = 1
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertEqual(metadata.purpose, MetadataPurpose.CONNECT)

    # Test with valid case with interest list metadata has right metadata_follows
    def test__proc_connect_json_2_d(self):
        ex_index = 1
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertFalse(metadata.metadata_follows)

    # Test with valid case with interest list metadata has expected config_changes with the list
    def test__proc_connect_json_2_e(self):
        ex_index = 1
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertTrue(metadata.config_changes)

    # Test with JSON that doesn't deserialize to object that metadata is None
    def test__proc_connect_json_3_a(self):
        ex_index = 2
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertIsNone(metadata)

    # Test with JSON that doesn't deserialize to object that success is False
    def test__proc_connect_json_3_b(self):
        ex_index = 2
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertFalse(success)

    # Test with wrong metadata purpose in JSON that metadata object still is returned
    def test__proc_connect_json_4_a(self):
        ex_index = 3
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertIsInstance(metadata, MetadataMessage)

    # Test with wrong metadata purpose in JSON that success is False
    def test__proc_connect_json_4_b(self):
        ex_index = 3
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertFalse(success)

    # Test with wrong metadata purpose in JSON that metadata has wrong purpose
    def test__proc_connect_json_4_c(self):
        ex_index = 3
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertNotEquals(metadata.purpose, MetadataPurpose.CONNECT)

    # Test with wrong metadata_follows in JSON metadata object is still deserialized
    def test__proc_connect_json_5_a(self):
        ex_index = 4
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertIsInstance(metadata, MetadataMessage)

    # Test with wrong metadata_follows in JSON that success is False
    def test__proc_connect_json_5_b(self):
        ex_index = 4
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertFalse(success)

    # Test with wrong metadata_follows in JSON metadata object has wrong metadata_follows (i.e., True)
    def test__proc_connect_json_5_d(self):
        ex_index = 4
        service = self._services[0]
        conn_id = str(uuid.uuid4())

        metadata_json = self._connect_metadata_examples[ex_index]
        metadata, success, r_txt = service._proc_connect_json(json_msg=metadata_json, conn_id=conn_id)
        self.assertTrue(metadata.metadata_follows)

    # TODO: tests for _dequeue_monitored_change(self, connection_id: str)

    # TODO: tests for _enqueue_monitored_change(self, change_obj: MonitoredChange)

    # TODO: tests for _get_interested_connections(self, job_id: str)

    # TODO: tests for _is_connection_interested(self, connection_id: str, job_id: str)

    # TODO: tests for _proc_metadata_jobs_of_interest(self, metadata_obj: MetadataMessage)

    # TODO: tests for handle_connection_begin(self, message: str) -> Tuple[str, Optional[MetadataMessage], MetadataResponse]

    # TODO: tests for run_monitor_check(self)
