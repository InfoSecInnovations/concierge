from script_builder.util import get_venv_executable, is_unix, get_lines


def test_get_venv_executable():
    path = get_venv_executable()
    if is_unix:
        assert path == "bin/python"
    else:
        assert path == "Scripts\\python"


def test_get_lines():
    lines = get_lines(
        [
            get_venv_executable(),
            "script_builder_package/tests/printer.py",
            "line1",
            "",
            "line2",
        ]
    )
    assert lines == ["line1", "line2"]
