import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from ..scheduler.rsa_key_pair import RsaKeyPair
from typing import Dict


class TestRsaKeyPair(unittest.TestCase):

    def setUp(self) -> None:
        self.rsa_key_pairs: Dict[int, RsaKeyPair] = dict()
        self.rsa_key_pairs[1] = RsaKeyPair(directory='.', name='id_rsa_1')

        self.serial_rsa_key_pairs: Dict[int, dict] = dict()
        self.serial_rsa_key_pairs[1] = self.rsa_key_pairs[1].to_dict()


    def tearDown(self) -> None:
        self.rsa_key_pairs[1].private_key_file.unlink(missing_ok=True)
        self.rsa_key_pairs[1].public_key_file.unlink(missing_ok=True)

    def test_generate_key_pair_1_a(self):
        """
        Test that the first testing key pair generates and writes a private key file.
        """
        key_pair = self.rsa_key_pairs[1]
        key_pair.write_key_files()
        self.assertTrue(key_pair.private_key_file.exists())

    def test_generate_key_pair_1_b(self):
        """
        Test that the first testing key pair generates and writes a public key file.
        """
        key_pair = self.rsa_key_pairs[1]
        key_pair.write_key_files()
        self.assertTrue(key_pair.public_key_file.exists())

    def test_generate_key_pair_1_c(self):
        """
        Test that the first testing key pair generates and writes a private key file that can be reserialized.
        """
        key_pair = self.rsa_key_pairs[1]
        key_pair.write_key_files()
        # This should result in the same file names as key_pair, and so the constructor should resolve that it needs to
        # load the key, not regenerate it
        reserialized_key = RsaKeyPair(directory=key_pair.directory, name=key_pair.name)
        self.assertEqual(key_pair, reserialized_key)

    def test_generate_key_pair_1_d(self):
        """
        Test that the first testing key pair generates and writes a private key file that can be reserialized with the
        same private key value.
        """
        key_pair = self.rsa_key_pairs[1]
        key_pair.write_key_files()
        # This should result in the same file names as key_pair, and so the constructor should resolve that it needs to
        # load the key, not regenerate it
        reserialized_key = RsaKeyPair(directory=key_pair.directory, name=key_pair.name)
        self.assertTrue(key_pair.private_key, reserialized_key.private_key)

    def test_generate_key_pair_1_e(self):
        """
        Test that the first testing key pair generates and writes a private key file that can be reserialized with the
        same private key PEM value.
        """
        key_pair = self.rsa_key_pairs[1]
        key_pair.write_key_files()
        # This should result in the same file names as key_pair, and so the constructor should resolve that it needs to
        # load the key, not regenerate it
        reserialized_key = RsaKeyPair(directory=key_pair.directory, name=key_pair.name)
        self.assertEqual(key_pair.private_key_pem, reserialized_key.private_key_pem)

    def test_generate_key_pair_1_from_dict_a(self):
        """
        """
        key_pair = self.rsa_key_pairs[1]
        key_pair.write_key_files()
        # This should result in the same file names as key_pair, and so the constructor should resolve that it needs to
        # load the key, not regenerate it

        key_pair_dict = key_pair.to_dict()
        key_pair_from_dict = RsaKeyPair.factory_init_from_deserialized_json(key_pair_dict)
        self.assertEqual(key_pair_from_dict, key_pair)

    def test_delete_key_files(self):
        """
        Verify that the `delete_key_files` method deletes both public and private key _if they
        exist_ to start with.
        """
        key_pair = self.rsa_key_pairs[1]
        key_pair.delete_key_files()
        self.assertFalse(key_pair.private_key_file.exists())
        self.assertFalse(key_pair.public_key_file.exists())

    def test_factory_init_from_deserialized_json_does_not_write_key_files_on_init(self):
        """
        verify key files are not created if they do not already exist on factory init.
        """
        key_pair = self.rsa_key_pairs[1]
        kp_as_dict = key_pair.to_dict()
        key_pair.delete_key_files()

        kp_from_factory = RsaKeyPair.factory_init_from_deserialized_json(kp_as_dict)

        assert kp_from_factory is not None
        self.assertFalse(kp_from_factory.private_key_file.exists())
        self.assertFalse(kp_from_factory.public_key_file.exists())

    def test_factory_init_from_deserialized_json_verifies_private_key_matches_successfully(self):
        """
        verify key files are not created if they do not already exist on factory init.
        """
        key_pair = self.rsa_key_pairs[1]
        self.assertTrue(key_pair.private_key_file.exists())

        kp_as_dict = key_pair.to_dict()
        kp_from_factory = RsaKeyPair.factory_init_from_deserialized_json(kp_as_dict)
        assert kp_from_factory is not None
        # this should have been called in __init__
        kp_from_factory._delete_existing_key_files_if_priv_keys_differ() # type: ignore
        self.assertTrue(kp_from_factory.private_key_file.exists())

    def test_factory_init_from_deserialized_json_does_not_write_pub_key_file_when_priv_exists(self):
        """
        verify pub key file is not created by factory init if priv key file already exists.
        are not created if they do not already exist on factory init.
        """
        key_pair = self.rsa_key_pairs[1]
        self.assertTrue(key_pair.private_key_file.exists())
        self.assertTrue(key_pair.public_key_file.exists())

        key_pair.public_key_file.unlink(missing_ok=True)
        self.assertFalse(key_pair.public_key_file.exists())

        kp_as_dict = key_pair.to_dict()
        kp_from_factory = RsaKeyPair.factory_init_from_deserialized_json(kp_as_dict)
        assert kp_from_factory is not None

        # main concern being tested
        self.assertFalse(kp_from_factory.public_key_file.exists())

        self.assertTrue(kp_from_factory.private_key_file.exists())

    def test_factory_init_from_deserialized_json_is_deserialized(self):
        """
        verify object `is_deserialized` property is true on factory init with no key files on disk.
        """
        key_pair = self.rsa_key_pairs[1]

        kp_as_dict = key_pair.to_dict()

        # remove key files
        key_pair.delete_key_files()
        self.assertFalse(key_pair.private_key_file.exists())
        self.assertFalse(key_pair.public_key_file.exists())

        kp_from_factory = RsaKeyPair.factory_init_from_deserialized_json(kp_as_dict)
        assert kp_from_factory is not None

        # main concern being tested
        self.assertTrue(kp_from_factory.is_deserialized)

    def test_factory_init_from_deserialized_json_is_deserialized_with_key_files_present(self):
        """
        verify object `is_deserialized` property is true on factory init key files on disk.
        """
        key_pair = self.serial_rsa_key_pairs[1]

        kp_from_factory = RsaKeyPair.factory_init_from_deserialized_json(key_pair)
        assert kp_from_factory is not None

        # main concern being tested
        self.assertTrue(kp_from_factory.is_deserialized)

    def test_is_deserialized_is_false_when_key_is_generated(self):
        """
        verify object `is_deserialized` property is false when key is generated.
        """
        with TemporaryDirectory() as dir:
            key_pair = RsaKeyPair(directory=dir, name="test_is_deserialized")
            self.assertFalse(key_pair.is_deserialized)

    def test_is_deserialized_is_true_when_key_is_present(self):
        """
        verify object `is_deserialized` property is false when key is generated.
        """
        key_pair = self.rsa_key_pairs[1]
        kp = RsaKeyPair(directory=key_pair.directory, name=key_pair.name)
        self.assertTrue(kp.is_deserialized)

    def test_reassign_directory_to_default(self):
        """
        verify object `is_deserialized` property is false when key is generated.
        """
        key_pair = self.rsa_key_pairs[1]
        default_location = Path.home() / ".ssh"
        self.assertNotEqual(key_pair.directory, default_location)

        o_pub_key = key_pair.public_key_file
        o_priv_key = key_pair.private_key_file

        key_pair.directory = None
        self.assertEqual(key_pair.directory, default_location)

        # remove original public key and private key
        o_priv_key.unlink(missing_ok=True)
        o_pub_key.unlink(missing_ok=True)

    def test_reassign_directory_creates_directory_if_not_exist(self):
        """
        verify object `is_deserialized` property is false when key is generated.
        """
        key_pair = self.rsa_key_pairs[1]
        with TemporaryDirectory() as dir:
            dir = Path(dir)
            new_dir = dir / ".ssh"

            self.assertFalse(new_dir.exists())
            self.assertNotEqual(key_pair.directory, new_dir)

            key_pair.directory = new_dir

            self.assertTrue(new_dir.exists())
            self.assertEqual(key_pair.directory, new_dir)
