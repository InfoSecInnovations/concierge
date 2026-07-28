import pytest
import os

if os.getenv("SHABTI_SECURITY_ENABLED") == "False":
    pytest.skip(reason="security not enabled", allow_module_level=True)
