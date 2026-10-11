import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def admin_token():
    resp = client.post("/api/v1/auth/login", json={"email": "admin@hospital.com", "password": "Admin@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def patient_token():
    resp = client.post("/api/v1/auth/login", json={"email": "patient@hospital.com", "password": "Patient@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_analytics_rbac_protection(patient_token, admin_token):
    # Patient role is forbidden from viewing operational intelligence
    res = client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {patient_token}"})
    assert res.status_code == 403

    # Unauthenticated is rejected
    res = client.get("/api/v1/analytics/overview")
    assert res.status_code == 401

    # Staff is permitted
    res = client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200


def test_analytics_overview_metrics(admin_token):
    res = client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    # Integrity assertions
    assert data["total_appointments"] > 0
    total = data["total_appointments"]
    parts = data["completed_count"] + data["no_show_count"] + data["cancelled_count"] + data["scheduled_count"]
    assert total == parts

    # Rate checks
    assert 0 <= data["no_show_rate_pct"] <= 100
    assert 0 <= data["cancellation_rate_pct"] <= 100
    assert 0 <= data["completion_rate_pct"] <= 100
    assert 0 <= data["slot_utilization_pct"] <= 100

    # Wait times checks
    assert data["avg_wait_time_minutes"] > 0
    assert data["median_wait_time_minutes"] > 0
    assert data["p90_wait_time_minutes"] >= data["median_wait_time_minutes"]
    assert data["avg_consultation_duration_minutes"] > 0


def test_analytics_waiting_times_report(admin_token):
    res = client.get("/api/v1/analytics/waiting-times", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert "by_department" in data
    assert "by_doctor" in data
    assert "by_time_slot" in data

    assert len(data["by_department"]) > 0
    for dept in data["by_department"]:
        assert dept["completed_count"] > 0
        assert dept["avg_wait_mins"] >= 0
        assert dept["p90_wait_mins"] >= dept["median_wait_mins"]

    assert len(data["by_doctor"]) > 0
    assert len(data["by_time_slot"]) > 0


def test_analytics_utilization_report(admin_token):
    res = client.get("/api/v1/analytics/utilization", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert "hourly_distribution" in data
    assert "day_of_week_distribution" in data
    assert "doctor_utilization" in data

    assert len(data["hourly_distribution"]) > 0
    assert len(data["day_of_week_distribution"]) > 0
    assert len(data["doctor_utilization"]) > 0


def test_analytics_cancellations_report(admin_token):
    res = client.get("/api/v1/analytics/cancellations", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert "by_department" in data
    assert "by_day_of_week" in data
    assert "common_reasons" in data

    assert len(data["by_department"]) > 0
    assert len(data["common_reasons"]) > 0


def test_analytics_no_shows_report(admin_token):
    res = client.get("/api/v1/analytics/no-shows", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert "by_department" in data
    assert "by_hour" in data
    assert "by_gender" in data

    assert len(data["by_department"]) > 0
    assert len(data["by_hour"]) > 0


def test_pre_ai_baseline_establishment(admin_token):
    res = client.get("/api/v1/analytics/baseline", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "BASELINE_ESTABLISHED"
    assert data["cohort_sample_size"] >= 1000
    benchmarks = data["benchmarks"]
    assert "baseline_no_show_rate_pct" in benchmarks
    assert "baseline_avg_wait_time_minutes" in benchmarks
    assert "baseline_slot_utilization_pct" in benchmarks

    targets = data["operational_target_with_ai"]
    assert targets["target_no_show_reduction_pct"] == 30.0
    assert targets["projected_no_show_rate_pct"] < benchmarks["baseline_no_show_rate_pct"]


def test_dashboard_ui_endpoint():
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "AI-HMS Operational Intelligence" in res.text
    assert "Chart.js" in res.text
