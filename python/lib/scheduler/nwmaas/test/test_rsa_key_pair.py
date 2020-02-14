import unittest
from ..scheduler.ssh_utils import RsaKeyPair


class TestRsaKeyPair(unittest.TestCase):

    def setUp(self) -> None:
        self.rsa_key_pairs = dict()
        self.rsa_key_pairs[1] = RsaKeyPair(directory='.', name='id_rsa_1')

    def tearDown(self) -> None:
        self.rsa_key_pairs[1].private_key_file.unlink()
        self.rsa_key_pairs[1].public_key_file.unlink()

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
        self.assertTrue(key_pair, reserialized_key)

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
        self.assertTrue(key_pair.private_key_pem, reserialized_key.private_key_pem)
