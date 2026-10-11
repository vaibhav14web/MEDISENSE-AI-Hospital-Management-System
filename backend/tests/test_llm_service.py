import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def admin_token():
    resp = client.post("/api/v1/auth/login", json={"email": "admin@hospital.com", "password": "Admin@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_llm_status_endpoint(admin_token):
    # Unauthenticated request is rejected
    res = client.get("/api/v1/llm/status")
    assert res.status_code == 401

    # Authenticated staff request returns status and tools
    res = client.get("/api/v1/llm/status", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "tools_available" in data
    assert "analyze_chest_xray" in data["tools_available"]
    assert "knowledge_base_records" in data
    assert data["knowledge_base_records"] > 0


def test_llm_chat_knowledge_query(admin_token):
    res = client.post(
        "/api/v1/llm/chat",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"message": "What is pneumonia and what are its symptoms?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert len(data["response"]) > 0
    assert "session_id" in data


def test_llm_chat_xray_tool_execution(admin_token):
    res = client.post(
        "/api/v1/llm/chat",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"message": "Please perform an xray radiograph evaluation on this chest scan."}
    )
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert data.get("tool_executed") == "analyze_chest_xray"
    assert data.get("tool_result") is not None
    assert "predicted_class" in data["tool_result"]
    assert "confidence" in data["tool_result"]
