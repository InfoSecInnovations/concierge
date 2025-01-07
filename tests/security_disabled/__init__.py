import pytest
from concierge_backend_lib.authorization import auth_enabled

if auth_enabled:
    pytest.skip("Security is enabled", allow_module_level=True)
