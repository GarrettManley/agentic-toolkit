import sys

from check import environment_report, python_version


def test_pytest_is_working():
    # If you can see this pass, uv + pytest are installed and running.
    assert True


def test_python_version_matches_interpreter():
    assert python_version() == (sys.version_info.major, sys.version_info.minor)


def test_python_is_3_12_or_newer():
    assert python_version() >= (3, 12)


def test_environment_report_has_expected_keys():
    assert set(environment_report()) >= {"python", "implementation"}
