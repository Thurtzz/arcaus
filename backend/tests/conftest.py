import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ember import build  # noqa: E402


@pytest.fixture(scope="session")
def bundle():
    b = build.build(write=True)  # always test the freshly built bundle
    return b


@pytest.fixture(scope="session")
def service(bundle):
    from ember.service import Service
    return Service(json.loads((ROOT / "data" / "build" / "evidence_bundle.json").read_text()))


@pytest.fixture(scope="session")
def client(bundle):
    from fastapi.testclient import TestClient
    import ember.service as svc
    svc._SERVICE = None
    from ember.api import app
    return TestClient(app)
