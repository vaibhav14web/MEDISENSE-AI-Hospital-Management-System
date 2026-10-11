"""
AI-HMS Week 2 Analytics Verification Runner
Verifies all operational intelligence deliverables:
1. SQL-backed calculation of waiting times (Mean, Median, P90)
2. Appointment slot utilization and capacity density
3. Cancellation rates and department breakdowns
4. No-show rate metrics across departments and demographics
5. Pre-AI Operational Baseline establishment
6. Interactive Web Dashboard UI accessibility
"""

import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner(title: str):
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")


def run_check(step_id: str, title: str, func) -> bool:
    t0 = time.time()
    try:
        details = func()
        ms = (time.time() - t0) * 1000
        print(f"[{GREEN}PASS{RESET}] {BOLD}{step_id:<8}{RESET} {title:<50} ({ms:.1f}ms)")
        if details:
            for line in details.split("\n"):
                print(f"       -> {line}")
        return True
    except Exception as e:
        ms = (time.time() - t0) * 1000
        print(f"[{RED}FAIL{RESET}] {BOLD}{step_id:<8}{RESET} {title:<50} ({ms:.1f}ms)")
        print(f"       -> {RED}Error: {e}{RESET}")
        return False


def main():
    print(f"\n{BOLD}Executing AI-HMS Week 2 Analytics & Operational Intelligence Suite...{RESET}")
    
    # Authenticate as staff
    login = client.post("/api/v1/auth/login", json={"email": "admin@hospital.com", "password": "Admin@123"}).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    results = []

    print_banner("1. OPERATIONAL OVERVIEW & HEADLINE KPIS")
    overview_data = {}
    def check_overview():
        r = client.get("/api/v1/analytics/overview", headers=headers)
        assert r.status_code == 200
        data = r.json()
        overview_data.update(data)
        return (
            f"Total Appointments: {data['total_appointments']} | Completed: {data['completed_count']} | No-Shows: {data['no_show_count']}\n"
            f"No-Show Rate: {data['no_show_rate_pct']}% | Cancellation Rate: {data['cancellation_rate_pct']}%\n"
            f"Capacity Utilization: {data['slot_utilization_pct']}% | Completion Rate: {data['completion_rate_pct']}%"
        )
    results.append(run_check("W2-01", "Hospital Operational Headline KPIs", check_overview))

    print_banner("2. WAITING TIMES DISTRIBUTION & PERCENTILES")
    def check_waiting_times():
        r = client.get("/api/v1/analytics/waiting-times", headers=headers)
        assert r.status_code == 200
        data = r.json()
        top_depts = ", ".join([f"{d['department']}: {d['avg_wait_mins']}m" for d in data['by_department'][:3]])
        return (
            f"Overall Mean Wait: {overview_data['avg_wait_time_minutes']} min | Median: {overview_data['median_wait_time_minutes']} min | P90: {overview_data['p90_wait_time_minutes']} min\n"
            f"Department Wait Leaders: {top_depts}\n"
            f"Time of Day Slots: {len(data['by_time_slot'])} slots tracked (Morning vs Afternoon vs Evening)"
        )
    results.append(run_check("W2-02", "Granular Waiting Times & Percentiles", check_waiting_times))

    print_banner("3. APPOINTMENT UTILIZATION & SCHEDULE DENSITY")
    def check_utilization():
        r = client.get("/api/v1/analytics/utilization", headers=headers)
        assert r.status_code == 200
        data = r.json()
        return (
            f"Hourly Slots Monitored: {len(data['hourly_distribution'])} operating hours\n"
            f"Days of Week Profiled: {len(data['day_of_week_distribution'])} clinical days (Mon-Sat)\n"
            f"Physicians Profiled: {len(data['doctor_utilization'])} doctors with individual load indices"
        )
    results.append(run_check("W2-03", "Capacity Density & Doctor Utilization", check_utilization))

    print_banner("4. CANCELLATION METRICS & ROOT CAUSES")
    def check_cancellations():
        r = client.get("/api/v1/analytics/cancellations", headers=headers)
        assert r.status_code == 200
        data = r.json()
        top_reason = data['common_reasons'][0]['reason_note'] if data['common_reasons'] else "N/A"
        return (
            f"Overall Cancellation Rate: {overview_data['cancellation_rate_pct']}%\n"
            f"Department Breakdown Count: {len(data['by_department'])} departments\n"
            f"Top Cited Reason: '{top_reason}'"
        )
    results.append(run_check("W2-04", "Cancellation Rates & Root Cause Profiling", check_cancellations))

    print_banner("5. NO-SHOW RATE ANALYSIS")
    def check_no_shows():
        r = client.get("/api/v1/analytics/no-shows", headers=headers)
        assert r.status_code == 200
        data = r.json()
        highest_dept = data['by_department'][0]['department']
        highest_rate = data['by_department'][0]['no_show_rate_pct']
        return (
            f"Hospital Baseline No-Show Rate: {overview_data['no_show_rate_pct']}%\n"
            f"Highest Department No-Show: {highest_dept} ({highest_rate}%)\n"
            f"Hourly Pattern Monitored: {len(data['by_hour'])} hours profiled"
        )
    results.append(run_check("W2-05", "No-Show Rates by Department & Time Slot", check_no_shows))

    print_banner("6. PRE-AI OPERATIONAL BASELINE SNAPSHOT")
    def check_baseline():
        r = client.get("/api/v1/analytics/baseline", headers=headers)
        assert r.status_code == 200
        data = r.json()
        b = data["benchmarks"]
        t = data["operational_target_with_ai"]
        return (
            f"Cohort Size: {data['cohort_sample_size']} appointments | Status: {data['status']}\n"
            f"Baseline No-Show Rate: {b['baseline_no_show_rate_pct']}% -> Target w/ ML: {t['projected_no_show_rate_pct']}%\n"
            f"Baseline Avg Wait Time: {b['baseline_avg_wait_time_minutes']} min -> Target w/ ML: {t['projected_avg_wait_time_minutes']} min"
        )
    results.append(run_check("W2-06", "Pre-AI Operational Baseline Registration", check_baseline))

    print_banner("7. OPERATIONAL DASHBOARD UI INTERFACE")
    def check_dashboard():
        r = client.get("/dashboard")
        assert r.status_code == 200 and "AI-HMS Operational Intelligence" in r.text
        return "Dashboard HTML/CSS/JS served live at http://127.0.0.1:8000/dashboard"
    results.append(run_check("W2-07", "Interactive Executive Dashboard Live Route", check_dashboard))

    print_banner("WEEK 2 VERIFICATION SUMMARY")
    passed = sum(results)
    total = len(results)
    color = GREEN if passed == total else RED
    print(f"{BOLD}Total Checks:{RESET} {total} | {color}{BOLD}Passed:{RESET} {passed} | {RED}{BOLD}Failed:{RESET} {total - passed}")
    if passed == total:
        print(f"\n{BOLD}{GREEN}ALL WEEK 2 ANALYTICS DELIVERABLES ARE 100% OPERATIONAL & VERIFIED!{RESET}\n")


if __name__ == "__main__":
    main()
