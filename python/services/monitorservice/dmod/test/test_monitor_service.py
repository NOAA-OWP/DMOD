import unittest
import uuid
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from dmod.core.execution import AllocationParadigm
from dmod.core.meta_data import TimeRange, StandardDatasetIndex
from dmod.communication import NGENRequest, NGENRequestBody
from ..monitorservice.service import Monitor, MonitorService, Job, JobStatus, MetadataMessage, MetadataPurpose,\
    MonitoredChange, MetadataResponse
from dmod.scheduler.job import JobExecPhase, JobImpl, JobExecStep


class MockMonitor(Monitor):

    def __init__(self, monitored_jobs: List[Job] = None):
        self.jobs = monitored_jobs if monitored_jobs else []

    @property
    def jobs(self) -> List[Job]:
        return self._jobs

    @jobs.setter
    def jobs(self, jobs: List[Job]):
        self._jobs = jobs
        self.previous_statuses: Dict[str, JobStatus] = dict()
        for j in self.jobs:
            self.previous_statuses[j.job_id] = j.status

    def get_jobs_to_monitor(self) -> List[Job]:
        return self.jobs

    def monitor_job(self, job: Job) -> Optional[Tuple[JobStatus, JobStatus]]:
        """
        Monitor a given job for changed status.

        Check whether the job modeled by the given object has changed in status, relative to an expected previous
        status.  When there is a change, return the previous and updated status values respectively.

        Updated status is read from the job object. Previous statuses are stored in a dedicated
        ::attribute:`previous_statuses` dictionary in this mock testing class.

        When the status differ, the previous status value is saved in a local variable, and the object's attribute is
        updated to the "new" previous value, and then this method returns.

        Parameters
        ----------
        job: Job
            The job to check.

        Returns
        -------
        Optional[Tuple[JobStatus, JobStatus]]
            ``None`` when the job has not changed status, or a tuple of its previous and updated status when different.
        """
        if job.status == self.previous_statuses[job.job_id]:
            return None
        previous = self.previous_statuses[job.job_id]
        self.previous_statuses[job.job_id] = job.status
        return previous, job.status


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


class TestMonitorService(unittest.TestCase):

    def setUp(self) -> None:
        self._conn_id = '00000000-0000-0000-0000-000000000000'
        self._other_conn_id_1 = '00000000-0000-0000-0000-000000000001'
        self._services = []
        # First one has no actual monitor
        self._services.append(MockMonitorService(MockMonitor()))

        self._jobs = []
        for i in range(3):
            self._jobs.append(
                JobImpl(
                    cpu_count=4,
                    memory_size=1000,
                    model_request=NGENRequest(
                        cpu_count=1,
                        allocation_paradigm=AllocationParadigm.SINGLE_NODE,
                        session_secret="52204a2f-8924-48b4-abab-d289ac5aedf7",
                        request_body=NGENRequestBody(
                            bmi_config_data_id="52204a2f-8924-48b4-abab-d289ac5aedf7",
                            catchments=None,
                            forcings_data_id="52204a2f-8924-48b4-abab-d289ac5aedf7",
                            hydrofabric_data_id="52204a2f-8924-48b4-abab-d289ac5aedf7",
                            hydrofabric_uid="52204a2f-8924-48b4-abab-d289ac5aedf7",
                            partition_cfg_data_id="52204a2f-8924-48b4-abab-d289ac5aedf7",
                            realization_config_data_id="52204a2f-8924-48b4-abab-d289ac5aedf7",
                            time_range=TimeRange(
                                variable=StandardDatasetIndex.TIME,
                                begin=datetime(2022, 1, 1),
                                end=datetime(2022, 1, 2),
                            ),
                        ),
                    ),
                    allocation_paradigm=AllocationParadigm.SINGLE_NODE,
                )
            )

        self._second_meta_ex_job_id = '52204a2f-8924-48b4-abab-d289ac5aedf7'

        self._connect_metadata_examples = []
        # Good, no interest list
        self._connect_metadata_examples.append('{"purpose": "CONNECT", "additional_metadata": false}')
        self._with_interest_ex = '{{"purpose": "CONNECT", '
        self._with_interest_ex += '"config_changes": {{"' + MonitorService.get_jobs_of_interest_config_key() + '": '
        self._with_interest_ex += '{job_id_list}}}, '
        self._with_interest_ex += '"additional_metadata": false}}'
        meta_ex_2 = self._with_interest_ex.format(job_id_list='["' + self._second_meta_ex_job_id + '"]')
        self._connect_metadata_examples.append(meta_ex_2)
        self._connect_metadata_examples.append('{"additional_metadata": false}')
        self._connect_metadata_examples.append('{"purpose": "PROMPT", "additional_metadata": false}')
        self._connect_metadata_examples.append('{"purpose": "CONNECT", "additional_metadata": true}')

        self._jobs[0].set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._jobs[1].set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_SCHEDULING))
        self._jobs[2].set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.SCHEDULED))

        self._services.append(MockMonitorService(MockMonitor(monitored_jobs=self._jobs)))

        self._original_statuses = []
        for j in self._jobs:
            self._original_statuses.append(j.status)

        self._jobs[0].set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_SCHEDULING))
        self._jobs[1].set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.SCHEDULED))
        self._jobs[2].set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.RUNNING))

        self._job_ids = list()
        self._jobs_by_id = dict()
        for j in self._jobs:
            self._job_ids.append(j.job_id)
            self._jobs_by_id[j.job_id] = j

        self._change_examples = []
        for i in range(len(self._jobs)):
            self._change_examples.append(MonitoredChange(job=self._jobs[i],
                                                         original_status=self._original_statuses[i],
                                                         connection_id=self._conn_id))

    def tearDown(self) -> None:
        pass

    def _generate_all_status_values(self) -> List[JobStatus]:
        all_statuses = []
        for phase in JobExecPhase:
            for step in JobExecStep:
                all_statuses.append(JobStatus(phase, step))
        return all_statuses

    # Test object type for simple example change example for job
    def test__generate_update_msg_1_a(self):
        change = self._change_examples[0]

        update = MonitorService._generate_update_msg(change)
        self.assertEqual(change.job.__class__, update.object_type)

    # Test object id for simple example change example for job
    def test__generate_update_msg_1_b(self):
        change = self._change_examples[0]

        update = MonitorService._generate_update_msg(change)
        self.assertEqual(change.job.job_id, update.object_id)

    # Test correct key in update data for simple example change example for job
    def test__generate_update_msg_1_c(self):
        change = self._change_examples[0]

        update = MonitorService._generate_update_msg(change)
        self.assertTrue('status' in update.updated_data)

    # Test correct value in update data for simple example change example for job
    def test__generate_update_msg_1_d(self):
        change = self._change_examples[0]

        update = MonitorService._generate_update_msg(change)
        self.assertEqual(update.updated_data['status'], str(change.job.status))

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

        random_job_id = self._second_meta_ex_job_id
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

        random_job_id = self._second_meta_ex_job_id
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

        random_job_id = self._second_meta_ex_job_id
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
        self.assertNotEqual(metadata.purpose, MetadataPurpose.CONNECT)

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

    # Test that when there are no monitored changes None is returned
    def test__dequeue_monitored_change_1_a(self):
        ind = 0
        service = self._services[ind]

        self.assertIsNone(service._dequeue_monitored_change(self._conn_id))

    # Test that when there are no monitored changes for this connection (but are for others) None is still returned
    def test__dequeue_monitored_change_1_b(self):
        ind = 0
        service = self._services[ind]

        if self._other_conn_id_1 not in service._mapped_change_queues_by_connection:
            service._mapped_change_queues_by_connection[self._other_conn_id_1] = list(self._change_examples)
        else:
            service._mapped_change_queues_by_connection[self._other_conn_id_1].extend(self._change_examples)

        self.assertIsNone(service._dequeue_monitored_change(self._conn_id))

    # Test that when there are monitored changes for this connection the expected is returned
    def test__dequeue_monitored_change_1_c(self):
        ind = 0
        service = self._services[ind]

        if self._conn_id not in service._mapped_change_queues_by_connection:
            service._mapped_change_queues_by_connection[self._conn_id] = list(self._change_examples)
        else:
            self.assertTrue(False)

        self.assertEqual(service._dequeue_monitored_change(self._conn_id), self._change_examples[0])

    # Test that when there are monitored changes for this connection the expected is returned
    def test__dequeue_monitored_change_1_d(self):
        ind = 0
        service = self._services[ind]

        if self._conn_id not in service._mapped_change_queues_by_connection:
            service._mapped_change_queues_by_connection[self._conn_id] = list(self._change_examples)
        else:
            self.assertTrue(False)

        service._dequeue_monitored_change(self._conn_id)

        self.assertEqual(service._dequeue_monitored_change(self._conn_id), self._change_examples[1])

    # Test that when there are monitored changes for this connection the expected is returned
    def test__dequeue_monitored_change_1_e(self):
        ind = 0
        service = self._services[ind]

        if self._conn_id not in service._mapped_change_queues_by_connection:
            service._mapped_change_queues_by_connection[self._conn_id] = list(self._change_examples)
        else:
            self.assertTrue(False)

        service._dequeue_monitored_change(self._conn_id)
        service._dequeue_monitored_change(self._conn_id)

        self.assertEqual(service._dequeue_monitored_change(self._conn_id), self._change_examples[2])

    # Test that when there are monitored changes, but after all have been removed, None is returned again
    def test__dequeue_monitored_change_1_f(self):
        ind = 0
        service = self._services[ind]

        if self._conn_id not in service._mapped_change_queues_by_connection:
            service._mapped_change_queues_by_connection[self._conn_id] = list(self._change_examples)
        else:
            self.assertTrue(False)

        service._dequeue_monitored_change(self._conn_id)
        service._dequeue_monitored_change(self._conn_id)
        service._dequeue_monitored_change(self._conn_id)

        self.assertIsNone(service._dequeue_monitored_change(self._conn_id))

    # Test that enqueue works with one example
    def test__enqueue_monitored_change_1_a(self):
        ind = 0
        service = self._services[0]
        change = self._change_examples[ind]

        service._enqueue_monitored_change(change)
        self.assertEqual(service._dequeue_monitored_change(connection_id=change.connection_id), change)

    # Test that enqueue works with one example
    def test__enqueue_monitored_change_2_a(self):
        ind = 1
        service = self._services[0]
        change = self._change_examples[ind]

        service._enqueue_monitored_change(change)
        self.assertEqual(service._dequeue_monitored_change(connection_id=change.connection_id), change)

    # Test that enqueue works with one example
    def test__enqueue_monitored_change_3_a(self):
        ind = 2
        service = self._services[0]
        change = self._change_examples[ind]

        service._enqueue_monitored_change(change)
        self.assertEqual(service._dequeue_monitored_change(connection_id=change.connection_id), change)

    # Test that enqueue works with multiple changes, and order is correct
    def test__enqueue_monitored_change_4_a(self):
        service = self._services[0]

        for i in range(len(self._change_examples)):
            service._enqueue_monitored_change(self._change_examples[i])

        for k in range(len(self._change_examples)):
            self.assertEqual(service._dequeue_monitored_change(self._conn_id), self._change_examples[k])

    # Test that nothing is initially interested in a random job id
    def test__get_interested_connections_1_a(self):
        service = self._services[0]
        random_job_id = self._second_meta_ex_job_id

        self.assertEqual(len(service._get_interested_connections(random_job_id)), 0)

    # Test that nothing is initially interested in randomly generated job ids
    def test__get_interested_connections_1_b(self):
        service = self._services[0]

        for i in range(0, 25):
            self.assertEqual(len(service._get_interested_connections(str(uuid.uuid4()))), 0)

    # Test that job is not of interest by default
    def test__get_interested_connections_2_a(self):
        service = self._services[0]
        job = self._jobs[0]
        job_id = job.job_id

        self.assertNotIn(self._conn_id, service._get_interested_connections(job_id))

    # Test that job is of interest by after connection registration that notes just that job is of interest
    def test__get_interested_connections_2_b(self):
        service = self._services[0]
        job = self._jobs[0]
        job_id = job.job_id

        conn_id = service.register_connection(self, [job_id])

        self.assertIn(conn_id, service._get_interested_connections(job_id))

    # Test that job is of interest by after connection registration that notes that job and others is of interest
    def test__get_interested_connections_2_c(self):
        service = self._services[0]
        job = self._jobs[0]
        job_id = job.job_id

        of_interest = [job_id]
        of_interest.append(self._jobs[1].job_id)
        of_interest.append(self._jobs[2].job_id)

        conn_id = service.register_connection(self, of_interest)

        self.assertIn(conn_id, service._get_interested_connections(job_id))

    # Test that job is of interest by after connection registration that notes that job and others of interest,
    # regardless of where in the list job in question is
    def test__get_interested_connections_2_d(self):
        service = self._services[0]
        job = self._jobs[1]
        job_id = job.job_id

        of_interest = []
        of_interest.append(self._jobs[0].job_id)
        of_interest.append(job_id)
        of_interest.append(self._jobs[2].job_id)

        conn_id = service.register_connection(self, of_interest)

        self.assertIn(conn_id, service._get_interested_connections(job_id))

    # Test that job is of interest by after connection registration that notes that job and others of interest to
    # multiple services
    def test__get_interested_connections_2_e(self):
        service = self._services[0]
        job = self._jobs[1]
        job_id = job.job_id

        of_interest = []
        of_interest.append(self._jobs[0].job_id)
        of_interest.append(job_id)
        of_interest.append(self._jobs[2].job_id)

        conn_id = service.register_connection(self, of_interest)
        conn_id_2 = service.register_connection(self, of_interest)

        self.assertIn(conn_id_2, service._get_interested_connections(job_id))
        self.assertIn(conn_id, service._get_interested_connections(job_id))

    # Test that None is returned if metadata doesn't have this field
    def test__proc_metadata_jobs_of_interest_1_a(self):
        service = self._services[0]
        metadata = MetadataMessage(purpose=MetadataPurpose.CONNECT)
        self.assertIsNone(service._proc_metadata_jobs_of_interest(metadata))

    # Test that when there are some of interest, that a list is returned
    def test__proc_metadata_jobs_of_interest_2_a(self):
        service = self._services[0]
        job_id_list = []
        for j in self._jobs:
            job_id_list.append(j.job_id)
        changes_map = dict()
        changes_map[MonitorService.get_jobs_of_interest_config_key()] = job_id_list

        metadata = MetadataMessage(purpose=MetadataPurpose.CONNECT, config_changes=changes_map)
        of_interest_ids = service._proc_metadata_jobs_of_interest(metadata)
        self.assertIsInstance(of_interest_ids, list)

    # Test that when there are some of interest, that the contents are correct (the right ids, and no extras)
    def test__proc_metadata_jobs_of_interest_2_b(self):
        service = self._services[0]
        job_id_list = []
        for j in self._jobs:
            job_id_list.append(j.job_id)
        changes_map = dict()
        changes_map[MonitorService.get_jobs_of_interest_config_key()] = job_id_list

        metadata = MetadataMessage(purpose=MetadataPurpose.CONNECT, config_changes=changes_map)
        of_interest_ids = service._proc_metadata_jobs_of_interest(metadata)
        for j in self._jobs:
            self.assertTrue(j.job_id in of_interest_ids)
        self.assertEqual(len(of_interest_ids), len(self._jobs))

    # Test with valid case with no interest list metadata is a metadata object
    def test_handle_connection_begin_1_a(self):
        ex_index = 0
        service = self._services[0]
        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertIsInstance(metadata, MetadataMessage)

    # Test with valid case with no interest list metadata has right purpose
    def test_handle_connection_begin_1_b(self):
        ex_index = 0
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertEqual(metadata.purpose, MetadataPurpose.CONNECT)

    # Test with valid case with no interest list metadata has right follows
    def test_handle_connection_begin_1_c(self):
        ex_index = 0
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertFalse(metadata.metadata_follows)

    # Test with valid case with no interest list response is correct type
    def test_handle_connection_begin_1_d(self):
        ex_index = 0
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertIsInstance(response, MetadataResponse)

    # Test with valid case with no interest list response is successful
    def test_handle_connection_begin_1_e(self):
        ex_index = 0
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertTrue(response.success)

    # Test with valid case with no interest list response shows right purpose
    def test_handle_connection_begin_1_f(self):
        ex_index = 0
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertEqual(response.purpose, MetadataPurpose.CONNECT)

    # Test with valid case with interest list metadata is a metadata object
    def test_handle_connection_begin_2_a(self):
        ex_index = 1
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertIsInstance(metadata, MetadataMessage)

    # Test with valid case with interest list metadata has right purpose
    def test_handle_connection_begin_2_b(self):
        ex_index = 1
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertEqual(metadata.purpose, MetadataPurpose.CONNECT)

    # Test with valid case with interest list metadata has right follows
    def test_handle_connection_begin_2_c(self):
        ex_index = 1
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertFalse(metadata.metadata_follows)

    # Test with valid case with interest list response is correct type
    def test_handle_connection_begin_2_d(self):
        ex_index = 1
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertIsInstance(response, MetadataResponse)

    # Test with valid case with interest list response is successful
    def test_handle_connection_begin_2_e(self):
        ex_index = 1
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertTrue(response.success)

    # Test with valid case with interest list response shows right purpose
    def test_handle_connection_begin_2_f(self):
        ex_index = 1
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertEqual(response.purpose, MetadataPurpose.CONNECT)

    # Test with valid case with interest list response sets jobs of interest properly
    def test_handle_connection_begin_2_g(self):
        ex_index = 1
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertTrue(service._is_connection_interested(connection_id=conn_id, job_id=self._second_meta_ex_job_id))

    # Test with invalid metadata JSON returns None for metadata object
    def test_handle_connection_begin_3_a(self):
        ex_index = 2
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertIsNone(metadata)

    # Test with invalid metadata JSON returns unsuccessful response
    def test_handle_connection_begin_3_b(self):
        ex_index = 2
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertFalse(response.success)

    # Test with wrong purpose in metadata JSON return metadata object
    def test_handle_connection_begin_4_a(self):
        ex_index = 3
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertIsInstance(metadata, MetadataMessage)

    # Test with wrong purpose in metadata JSON returns unsuccessful response
    def test_handle_connection_begin_4_b(self):
        ex_index = 3
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertFalse(response.success)

    # Test with wrong follows in metadata JSON return metadata object
    def test_handle_connection_begin_5_a(self):
        ex_index = 4
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertIsInstance(metadata, MetadataMessage)

    # Test with wrong follows in metadata JSON returns unsuccessful response
    def test_handle_connection_begin_5_b(self):
        ex_index = 4
        service = self._services[0]

        metadata_json = self._connect_metadata_examples[ex_index]
        conn_id, metadata, response = service.handle_connection_begin(metadata_json)
        self.assertFalse(response.success)

    # Test this finds the number of expected changes
    def test_run_monitor_check_1_a(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        changes_queue = service._mapped_change_queues_by_connection[conn_id]

        self.assertEqual(len(changes_queue), len(self._jobs))

    # Test this finds changes for the expected jobs
    def test_run_monitor_check_1_b(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        changes_queue = service._mapped_change_queues_by_connection[conn_id]
        # Changes by job id
        changes: Dict[str, MonitoredChange] = dict()
        while changes_queue:
            c = changes_queue.pop(0)
            changes[c.job.job_id] = c

        self.assertEqual(self._jobs_by_id.keys(), changes.keys())

    # Test correct original status values
    def test_run_monitor_check_1_c(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        changes_queue = service._mapped_change_queues_by_connection[conn_id]
        # Changes by job id
        changes: Dict[str, MonitoredChange] = dict()
        while changes_queue:
            c = changes_queue.pop(0)
            changes[c.job.job_id] = c
        for i in range(len(self._jobs)):
            self.assertEqual(changes[self._jobs[i].job_id].original_status, self._original_statuses[i])

    # Test correct updated status values
    def test_run_monitor_check_1_d(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        changes_queue = service._mapped_change_queues_by_connection[conn_id]
        # Changes by job id
        changes: Dict[str, MonitoredChange] = dict()
        while changes_queue:
            c = changes_queue.pop(0)
            changes[c.job.job_id] = c
        for i in range(len(self._jobs)):
            self.assertEqual(changes[self._jobs[i].job_id].job.status, self._jobs[i].status)

    # Test original status is different than updated status
    def test_run_monitor_check_1_e(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        changes_queue = service._mapped_change_queues_by_connection[conn_id]
        while changes_queue:
            c = changes_queue.pop(0)
            self.assertNotEqual(c.original_status, c.job.status)

    # Test that after first changes conveyed, if nothing done to jobs, second monitor shows no changed jobs
    def test_run_monitor_check_2_a(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        changes_queue = service._mapped_change_queues_by_connection[conn_id]
        while changes_queue:
            service._dequeue_monitored_change(conn_id)
        # Now run again
        service.run_monitor_check()
        self.assertFalse(changes_queue)

    # Test that after first changes conveyed, if nothing done to jobs, second monitor will immediately dequeue change of
    # None
    def test_run_monitor_check_2_b(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        change = service._dequeue_monitored_change(conn_id)
        while change is not None:
            change = service._dequeue_monitored_change(conn_id)
        # Now run again
        service.run_monitor_check()
        self.assertIsNone(service._dequeue_monitored_change(conn_id))

    # Test that after first changes conveyed, then something done, a single changed job is listed
    def test_run_monitor_check_3_a(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        change = service._dequeue_monitored_change(conn_id)
        while change is not None:
            change = service._dequeue_monitored_change(conn_id)

        # Now have there be another change to "monitor"
        job = self._jobs[1]
        original_status = job.status
        get_next_one = False
        for status in self._generate_all_status_values():
            if get_next_one:
                job.set_status(status)
                break
            elif status == original_status:
                get_next_one = True

        # Then monitor again
        service.run_monitor_check()
        new_changes = list()
        change = service._dequeue_monitored_change(conn_id)
        while change is not None:
            new_changes.append(change)
            change = service._dequeue_monitored_change(conn_id)

        self.assertEqual(len(new_changes), 1)

    # Test that after first changes conveyed, then something done, the right changed job is listed
    def test_run_monitor_check_3_b(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        change = service._dequeue_monitored_change(conn_id)
        while change is not None:
            change = service._dequeue_monitored_change(conn_id)

        # Now have there be another change to "monitor"
        job = self._jobs[1]
        original_status = job.status
        get_next_one = False

        for status in self._generate_all_status_values():
            if get_next_one:
                job.set_status(status)
                break
            elif status == original_status:
                get_next_one = True

        # Then monitor again
        service.run_monitor_check()
        change = service._dequeue_monitored_change(conn_id)

        self.assertEqual(change.job.job_id, job.job_id)

    # Test that after first changes conveyed, then something done, the right original status is listed
    def test_run_monitor_check_3_c(self):
        service = self._services[1]
        conn_id = service.register_connection(connection=self, jobs_of_interest=self._job_ids)
        service.run_monitor_check()
        change = service._dequeue_monitored_change(conn_id)
        while change is not None:
            change = service._dequeue_monitored_change(conn_id)

        # Now have there be another change to "monitor"
        job = self._jobs[1]
        original_status = job.status
        get_next_one = False
        for status in self._generate_all_status_values():
            if get_next_one:
                job.set_status(status)
                break
            elif status == original_status:
                get_next_one = True

        # Then monitor again
        service.run_monitor_check()
        change = service._dequeue_monitored_change(conn_id)

        self.assertEqual(change.original_status, original_status)
