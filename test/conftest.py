import unittest

import pytest


def pytest_configure():
    unittest.TestCase.maxDiff = None


# mark every test in folder collection as unit test
def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.unit)
