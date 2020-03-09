from unittest import TestCase
from ..redis.keynamehelper import KeyNameHelper


class TestKeyNameHelper(TestCase):

    def setUp(self) -> None:
        self.default_keynamehelper = KeyNameHelper.get_default_instance()
        self.helper_prefix_1 = KeyNameHelper(prefix='test_prefix', separator=KeyNameHelper.get_default_separator())
        self.helper_separator_1 = KeyNameHelper(prefix=KeyNameHelper.get_default_prefix(), separator='|')

    def test_create_key_name_1_a(self):
        """
        Test creating a key name using the default instance.
        """
        helper = self.default_keynamehelper

        key_name = helper.create_key_name("something", 'else', 'hello', 'test')
        self.assertEqual(key_name, ':something:else:hello:test')

    def test_create_key_name_2_a(self):
        """
        Test creating a key name using an instance with a modified prefix.
        """
        helper = self.helper_prefix_1

        key_name = helper.create_key_name("something", 'else', 'hello', 'test')
        self.assertEqual(key_name, 'test_prefix:something:else:hello:test')

    def test_create_field_name_1_a(self):
        """
        Test creating a field name using the default instance.
        """
        helper = self.default_keynamehelper

        field_name = helper.create_field_name("something", 'else', 'hello', 'test')
        self.assertEqual(field_name, 'something:else:hello:test')

    def test_create_field_name_2_a(self):
        """
        Test creating a field name using the default instance.
        """
        helper = self.helper_separator_1

        field_name = helper.create_field_name("something", 'else', 'hello', 'test')
        self.assertEqual(field_name, 'something|else|hello|test')

    def test_prefix_1_a(self):
        """
        Test getting the prefix with a default instance.
        """
        helper = self.default_keynamehelper

        self.assertEqual(helper.prefix, '')

    def test_prefix_2_a(self):
        """
        Test getting the prefix with a non-default instance.
        """
        helper = self.helper_prefix_1

        self.assertEqual(helper.prefix, 'test_prefix')

    def test_separator_1_a(self):
        """
        Test getting the separator with a default instance.
        """
        helper = self.default_keynamehelper

        self.assertEqual(helper.separator, ':')

    def test_separator_2_a(self):
        """
        Test getting the separator with a non-default instance.
        """
        helper = self.helper_separator_1

        self.assertEqual(helper.separator, '|')
