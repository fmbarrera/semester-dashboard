import pytest

from app import ALL_INTERFACES, LOCAL_ONLY, parse_args


def test_default_is_this_machine_only():
    assert parse_args([]).host == LOCAL_ONLY


def test_lan_opens_to_the_network():
    assert parse_args(["--lan"]).host == ALL_INTERFACES


def test_explicit_host_still_works():
    assert parse_args(["--host", "100.64.0.5"]).host == "100.64.0.5"


def test_lan_and_host_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit):
        parse_args(["--lan", "--host", "127.0.0.1"])
