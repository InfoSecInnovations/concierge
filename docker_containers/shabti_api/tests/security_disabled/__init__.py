import pytest
import os

pytest.skipif(
    os.getenv("SHABTI_SECURITY_ENABLED") == "True",
    reason="security enabled",
    allow_module_level=True,
)
