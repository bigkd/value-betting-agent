import importlib

import pytest

import vba

SUBPACKAGES = ["data", "model", "betting", "api", "agent", "mcp_server"]


def test_package_has_version():
    assert vba.__version__


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_is_importable(name):
    assert importlib.import_module(f"vba.{name}")
