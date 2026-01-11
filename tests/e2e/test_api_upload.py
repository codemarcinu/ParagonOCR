
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.receipt import Receipt

@pytest.fixture
def override_get_db(test_db):
    def _get_db():
        yield test_db
    app.dependency_overrides[get_db] = _get_db
    yield
    del app.dependency_overrides[get_db]

@pytest.fixture
def override_get_current_user(test_db):
    def _get_current_user():
        # Ensure user exists
        user = test_db.query(User).filter_by(email="test@example.com").first()
        if not user:
            user = User(email="test@example.com", hashed_password="pw", is_active=True)
            test_db.add(user)
            test_db.commit()
            test_db.refresh(user)
        return user
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    del app.dependency_overrides[get_current_user]

def test_upload_receipt_endpoint(override_get_db, override_get_current_user, test_db):
    client = TestClient(app)
    
    # Mock background tasks to avoid running actual OCR/LLM
    with patch("app.routers.receipts.process_receipt_task") as mock_task:
        # Create a dummy file
        files = {'file': ('receipt.jpg', b'fake image content', 'image/jpeg')}
        
        response = client.post("/api/receipts/analyze", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "id" in data
        assert data["status"] == "processing"
        assert data["source_file"] == "receipt.jpg"
        
        # Verify it was added to DB
        receipt = test_db.query(Receipt).filter(Receipt.id == data["id"]).first()
        assert receipt is not None
        assert receipt.status == "processing"
