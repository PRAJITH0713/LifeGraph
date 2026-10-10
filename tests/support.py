"""Keep the module-level Flask app isolated from local user data during tests."""

import os
import tempfile
from pathlib import Path


_test_runtime = tempfile.TemporaryDirectory(prefix="lifegraph-test-runtime-")
os.environ["LIFEGRAPH_DATABASE_PATH"] = str(
    Path(_test_runtime.name) / "module-app.db"
)
os.environ["LIFEGRAPH_UPLOAD_DIRECTORY"] = str(
    Path(_test_runtime.name) / "module-uploads"
)
