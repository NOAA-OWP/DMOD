import unittest
from ..core.decorators import deprecated

DEPRECATION_MESSAGE = "test is deprecated"

@deprecated(DEPRECATION_MESSAGE)
def deprecated_function():
    ...

class TestDeprecatedDecorator(unittest.TestCase):
    def test_raises_deprecated_warning(self):
        with self.assertWarns(DeprecationWarning):
            deprecated_function()
