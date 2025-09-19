import pytest
import os

pytest.skipif(
    os.getenv("SHABTI_SECURITY_ENABLED") == "False",
    reason="security not enabled",
    allow_module_level=True,
)
