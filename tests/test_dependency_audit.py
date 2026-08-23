"""Dependency audit script tests."""

from scripts.dependency_audit import package_name


def test_package_name_strips_specifier():
    assert package_name("bittensor>=10.5.0") == "bittensor"
    assert package_name("python-dotenv>=1.0.0") == "python-dotenv"
