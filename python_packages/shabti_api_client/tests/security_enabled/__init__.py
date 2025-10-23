import pytest
import os

if os.getenv("SHABTI_SECURITY_ENABLED") == "False":
    pytest.skip(reason="security disabled", allow_module_level=True)
