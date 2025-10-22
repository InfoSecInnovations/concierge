import pytest
import os

if os.getenv("SHABTI_SECURITY_ENABLED") == "True":
    pytest.skip(reason="security enabled", allow_module_level=True)
