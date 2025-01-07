from script_builder.util import get_venv_executable, is_unix


def test_get_venv_executable():
    path = get_venv_executable()
    if is_unix:
        assert path == "bin/python"
    else:
        assert path == "Scripts\\python"
