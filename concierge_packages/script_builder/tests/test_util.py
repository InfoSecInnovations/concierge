from script_builder.util import get_venv_executable, is_unix, get_install_status
import pytest


def test_get_venv_executable():
    path = get_venv_executable()
    if is_unix:
        assert path == "bin/python"
    else:
        assert path == "Scripts\\python"


def test_get_install_status(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    assert get_install_status("yes", "no")


def test_get_negative_install_status(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "no")
    with pytest.raises(SystemExit):
        get_install_status("yes", "no")


def test_get_neutral_install_status(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "blah")
    assert not get_install_status("yes", "no")
