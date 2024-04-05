import pathlib
import tempfile
import unittest

from dmod.dataservice.service_settings import ServiceSettings


class TestServiceSettings(unittest.TestCase):
    def test_creating_settings_object_from_env_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            object_store_username = "username"
            object_store_passwd = "password"
            ssl_dir = pathlib.Path(temp_dir)
            env_text = f"""
OBJECT_STORE_EXEC_USER_NAME='{object_store_username}'
OBJECT_STORE_EXEC_USER_PASSWD='{object_store_passwd}'
SSL_DIR='{ssl_dir!s}'
"""

            env_file = pathlib.Path(temp_dir) / ".env"
            assert env_file.write_text(env_text) == len(env_text)
            # the absence of a secrets dir should cause a warning.
            # check that is the case
            with self.assertWarns(UserWarning):
                settings = ServiceSettings(_env_file=env_file)

        assert settings.object_store_exec_user_name == object_store_username
        assert settings.object_store_exec_user_passwd == object_store_passwd
        assert settings.ssl_dir == ssl_dir

    def test_creating_settings_object_from_secrets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            object_store_username = "username"
            (pathlib.Path(temp_dir) / "object_store_exec_user_name").write_text(
                object_store_username
            )

            object_store_passwd = "password"
            (pathlib.Path(temp_dir) / "object_store_exec_user_passwd").write_text(
                object_store_passwd
            )

            ssl_dir = pathlib.Path(temp_dir)
            (pathlib.Path(temp_dir) / "ssl_dir").write_text(str(ssl_dir))

            settings = ServiceSettings(_secrets_dir=temp_dir)

        assert settings.object_store_exec_user_name == object_store_username
        assert settings.object_store_exec_user_passwd == object_store_passwd
        assert settings.ssl_dir == ssl_dir
