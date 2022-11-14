import unittest
from ..communication.maas_request import NGENCalibrationRequest
from dmod.core.meta_data import TimeRange


def create_time_range(begin, end, var=None) -> TimeRange:
    serialized = {
        "begin": begin,
        "end": end,
        "datetime_pattern": "%Y-%m-%d %H:%M:%S",
        "subclass": TimeRange.__name__,
        "variable": "Time" if var is None else var,
    }
    return TimeRange.factory_init_from_deserialized_json(serialized)


class TestNGENCalibrationRequest(unittest.TestCase):
    @property
    def time_range(self):
        return create_time_range("2022-01-01 00:00:00", "2022-03-01 00:00:00")

    @property
    def cat_ids_list(self):
        return ["cat-1", "cat-2", "cat-3"]

    def test_model_name_eq_ngen_cal(self):
        request = NGENCalibrationRequest(
            session_secret="f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c",
            cpu_count=1,
            allocation_paradigm="ROUND_ROBIN",
            time_range=self.time_range,
            hydrofabric_uid="0123456789",
            hydrofabric_data_id="9876543210",
            config_data_id="02468",
            bmi_cfg_data_id="02468",
            catchments=self.cat_ids_list,
        )
        self.assertEqual(request.model_name, NGENCalibrationRequest.model_name)

    def test_factory_init_from_deserialized_json(self):
        msg = {
            "model": {
                "name": "ngen_cal",
                "allocation_paradigm": "ROUND_ROBIN",
                "cpu_count": 0,
                "time_range": self.time_range.to_dict(),
                "hydrofabric_data_id": "9876543210",
                "hydrofabric_uid": "0123456789",
                "config_data_id": "02468",
                "bmi_config_data_id": "02468",
                "catchments": self.cat_ids_list,
            },
            "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c",
        }
        request = NGENCalibrationRequest.factory_init_from_deserialized_json(msg)
        self.maxDiff = None
        self.assertDictEqual(msg, request.to_dict())

    def test_factory_init_correct_response_subtype(self):
        msg = {
            "model": {
                "name": "ngen_cal",
                "allocation_paradigm": "ROUND_ROBIN",
                "cpu_count": 0,
                "time_range": self.time_range.to_dict(),
                "hydrofabric_data_id": "9876543210",
                "hydrofabric_uid": "0123456789",
                "config_data_id": "02468",
                "bmi_config_data_id": "02468",
                "catchments": self.cat_ids_list,
            },
            "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c",
        }
        request = (
            NGENCalibrationRequest.factory_init_correct_subtype_from_deserialized_json(
                msg
            )
        )

        self.assertEqual(request.model_name, NGENCalibrationRequest.model_name)
        # use `type()` instead of `isinstance()` for specificity.
        self.assertEqual(type(request), NGENCalibrationRequest)

if __name__ == "__main__":
    unittest.main()
