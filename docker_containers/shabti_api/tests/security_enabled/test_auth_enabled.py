from shabti_util import auth_enabled


def test_auth_setting():
    assert auth_enabled()
