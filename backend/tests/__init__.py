from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
