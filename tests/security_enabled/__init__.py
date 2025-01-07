import pytest
from concierge_backend_lib.authorization import auth_enabled

if not auth_enabled:
    pytest.skip("Security is disabled", allow_module_level=True)
