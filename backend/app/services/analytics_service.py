"""
Analytics & Operational Intelligence Service for AI-HMS
Calculates waiting times, utilization rates, cancellations, no-show rates,
and establishes the Pre-AI Operational Baseline.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session


class AnalyticsService:

    @staticmethod
    def get_overview_kpis(
        db: Session,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        department_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Calculates hospital-wide operational KPIs and headline metrics."""
        params: Dict[str, Any] = {}
        filters = []
        if from_date:
            filters.append("a.scheduled_at >= :from_date")
            params["from_date"] = from_date
        if to_date:
            filters.append("a.scheduled_at <= :to_date")
            params["to_date"] = to_date
        if department_id:
            filters.append("d.department_id = :dept_id")
            params["dept_id"] = department_id

        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

        query = text(f"""
            SELECT
                count(*) as total_appointments,
                count(case when a.status = 'completed' then 1 end) as completed_count,
                count(case when a.status = 'no_show' then 1 end) as no_show_count,
                count(case when a.status = 'cancelled' then 1 end) as cancelled_count,
                count(case when a.status = 'scheduled' then 1 end) as scheduled_count,
                round(avg(case when a.status = 'completed' and a.started_at is not null 
                    then EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0 end)::numeric, 1) as avg_wait_mins,
                round(percentile_cont(0.5) WITHIN GROUP (ORDER BY case when a.status = 'completed' and a.started_at is not null 
                    then EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0 end)::numeric, 1) as median_wait_mins,
                round(percentile_cont(0.9) WITHIN GROUP (ORDER BY case when a.status = 'completed' and a.started_at is not null 
                    then EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0 end)::numeric, 1) as p90_wait_mins,
                round(avg(case when a.status = 'completed' and a.started_at is not null and a.ended_at is not null 
                    then EXTRACT(EPOCH FROM (a.ended_at - a.started_at))/60.0 end)::numeric, 1) as avg_duration_mins
            FROM hospital.appointments a
            JOIN hospital.doctors d ON a.doctor_id = d.id
            {where_clause}
        """)

        row = db.execute(query, params).mappings().first()
        total = row["total_appointments"] or 0
        completed = row["completed_count"] or 0
        no_shows = row["no_show_count"] or 0
        cancelled = row["cancelled_count"] or 0
        scheduled = row["scheduled_count"] or 0

        # Concluded appointments (completed + no_show) form the denominator for no-show rate
        concluded = completed + no_shows
        no_show_rate = round((no_shows / concluded * 100.0), 2) if concluded > 0 else 0.0
        cancellation_rate = round((cancelled / total * 100.0), 2) if total > 0 else 0.0
        completion_rate = round((completed / total * 100.0), 2) if total > 0 else 0.0

        # Slot capacity utilization (attended vs booked slots)
        utilization_rate = round((completed / (total - cancelled) * 100.0), 2) if (total - cancelled) > 0 else 0.0

        return {
            "total_appointments": total,
            "completed_count": completed,
            "no_show_count": no_shows,
            "cancelled_count": cancelled,
            "scheduled_count": scheduled,
            "no_show_rate_pct": no_show_rate,
            "cancellation_rate_pct": cancellation_rate,
            "completion_rate_pct": completion_rate,
            "slot_utilization_pct": utilization_rate,
            "avg_wait_time_minutes": float(row["avg_wait_mins"] or 0.0),
            "median_wait_time_minutes": float(row["median_wait_mins"] or 0.0),
            "p90_wait_time_minutes": float(row["p90_wait_mins"] or 0.0),
            "avg_consultation_duration_minutes": float(row["avg_duration_mins"] or 0.0),
        }

    @staticmethod
    def get_waiting_times_report(
        db: Session,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculates waiting time distribution and granular breakdowns."""
        params: Dict[str, Any] = {}
        filters = ["a.status = 'completed'", "a.started_at IS NOT NULL"]
        if from_date:
            filters.append("a.scheduled_at >= :from_date")
            params["from_date"] = from_date
        if to_date:
            filters.append("a.scheduled_at <= :to_date")
            params["to_date"] = to_date

        where_clause = "WHERE " + " AND ".join(filters)

        # Department breakdown
        dept_query = text(f"""
            SELECT 
                coalesce(dep.name, 'Unassigned') as department,
                count(*) as completed_count,
                round(avg(EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0)::numeric, 1) as avg_wait_mins,
                round(percentile_cont(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0)::numeric, 1) as median_wait_mins,
                round(percentile_cont(0.9) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0)::numeric, 1) as p90_wait_mins,
                round(min(EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0)::numeric, 1) as min_wait_mins,
                round(max(EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0)::numeric, 1) as max_wait_mins
            FROM hospital.appointments a
            JOIN hospital.doctors d ON a.doctor_id = d.id
            LEFT JOIN hospital.departments dep ON d.department_id = dep.id
            {where_clause}
            GROUP BY coalesce(dep.name, 'Unassigned')
            ORDER BY avg_wait_mins DESC
        """)
        by_department = [dict(r) for r in db.execute(dept_query, params).mappings().all()]

        # Doctor breakdown
        doc_query = text(f"""
            SELECT 
                u.first_name || ' ' || coalesce(u.last_name, '') as doctor_name,
                coalesce(dep.name, 'General') as department,
                count(*) as completed_count,
                round(avg(EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0)::numeric, 1) as avg_wait_mins,
                round(percentile_cont(0.9) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0)::numeric, 1) as p90_wait_mins
            FROM hospital.appointments a
            JOIN hospital.doctors d ON a.doctor_id = d.id
            JOIN auth.users u ON d.user_id = u.id
            LEFT JOIN hospital.departments dep ON d.department_id = dep.id
            {where_clause}
            GROUP BY u.first_name, u.last_name, dep.name
            ORDER BY avg_wait_mins DESC
        """)
        by_doctor = [dict(r) for r in db.execute(doc_query, params).mappings().all()]

        # Time of day (Morning: <12, Afternoon: 12-15, Late: >15)
        time_query = text(f"""
            SELECT
                case 
                    when EXTRACT(HOUR FROM a.scheduled_at) < 13 then 'Morning (09:00 - 13:00)'
                    when EXTRACT(HOUR FROM a.scheduled_at) < 17 then 'Afternoon (13:00 - 17:00)'
                    else 'Evening (17:00+)'
                end as time_slot,
                count(*) as completed_count,
                round(avg(EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0)::numeric, 1) as avg_wait_mins,
                round(percentile_cont(0.9) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0)::numeric, 1) as p90_wait_mins
            FROM hospital.appointments a
            {where_clause}
            GROUP BY 1
            ORDER BY avg_wait_mins ASC
        """)
        by_time_slot = [dict(r) for r in db.execute(time_query, params).mappings().all()]

        return {
            "by_department": by_department,
            "by_doctor": by_doctor,
            "by_time_slot": by_time_slot,
        }

    @staticmethod
    def get_utilization_report(
        db: Session,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculates capacity density and appointment schedule utilization."""
        params: Dict[str, Any] = {}
        filters = []
        if from_date:
            filters.append("a.scheduled_at >= :from_date")
            params["from_date"] = from_date
        if to_date:
            filters.append("a.scheduled_at <= :to_date")
            params["to_date"] = to_date

        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

        # Hourly volume density
        hourly_query = text(f"""
            SELECT 
                EXTRACT(HOUR FROM a.scheduled_at)::int as hour,
                count(*) as total_booked,
                count(case when a.status = 'completed' then 1 end) as completed,
                count(case when a.status = 'no_show' then 1 end) as no_shows,
                round(count(case when a.status = 'completed' then 1 end) * 100.0 / nullif(count(*), 0), 1) as fulfillment_pct
            FROM hospital.appointments a
            {where_clause}
            GROUP BY EXTRACT(HOUR FROM a.scheduled_at)
            ORDER BY hour ASC
        """)
        hourly_distribution = [dict(r) for r in db.execute(hourly_query, params).mappings().all()]

        # Day of week distribution
        dow_query = text(f"""
            SELECT 
                to_char(a.scheduled_at, 'Day') as day_name,
                EXTRACT(ISODOW FROM a.scheduled_at)::int as day_number,
                count(*) as total_appointments,
                count(case when a.status = 'completed' then 1 end) as completed,
                round(avg(case when a.status = 'completed' and a.started_at is not null 
                    then EXTRACT(EPOCH FROM (a.started_at - a.scheduled_at))/60.0 end)::numeric, 1) as avg_wait_mins
            FROM hospital.appointments a
            {where_clause}
            GROUP BY to_char(a.scheduled_at, 'Day'), EXTRACT(ISODOW FROM a.scheduled_at)
            ORDER BY day_number ASC
        """)
        dow_distribution = [dict(r) for r in db.execute(dow_query, params).mappings().all()]

        # Doctor load ranking
        doc_query = text(f"""
            SELECT 
                u.first_name || ' ' || coalesce(u.last_name, '') as doctor_name,
                coalesce(dep.name, 'General') as department,
                count(*) as total_scheduled,
                count(case when a.status = 'completed' then 1 end) as completed,
                round(count(case when a.status = 'completed' then 1 end) * 100.0 / nullif(count(*), 0), 1) as utilization_pct
            FROM hospital.appointments a
            JOIN hospital.doctors d ON a.doctor_id = d.id
            JOIN auth.users u ON d.user_id = u.id
            LEFT JOIN hospital.departments dep ON d.department_id = dep.id
            {where_clause}
            GROUP BY u.first_name, u.last_name, dep.name
            ORDER BY total_scheduled DESC
        """)
        by_doctor = [dict(r) for r in db.execute(doc_query, params).mappings().all()]

        return {
            "hourly_distribution": hourly_distribution,
            "day_of_week_distribution": dow_distribution,
            "doctor_utilization": by_doctor,
        }

    @staticmethod
    def get_cancellations_report(
        db: Session,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculates cancellation metrics, rates by department, and reasons."""
        params: Dict[str, Any] = {}
        filters = []
        if from_date:
            filters.append("a.scheduled_at >= :from_date")
            params["from_date"] = from_date
        if to_date:
            filters.append("a.scheduled_at <= :to_date")
            params["to_date"] = to_date

        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

        # By Department
        dept_query = text(f"""
            SELECT 
                coalesce(dep.name, 'Unassigned') as department,
                count(*) as total_booked,
                count(case when a.status = 'cancelled' then 1 end) as cancelled_count,
                round(count(case when a.status = 'cancelled' then 1 end) * 100.0 / nullif(count(*), 0), 1) as cancellation_rate_pct
            FROM hospital.appointments a
            JOIN hospital.doctors d ON a.doctor_id = d.id
            LEFT JOIN hospital.departments dep ON d.department_id = dep.id
            {where_clause}
            GROUP BY coalesce(dep.name, 'Unassigned')
            ORDER BY cancellation_rate_pct DESC
        """)
        by_department = [dict(r) for r in db.execute(dept_query, params).mappings().all()]

        # By Day of week
        dow_query = text(f"""
            SELECT 
                to_char(a.scheduled_at, 'Day') as day_name,
                EXTRACT(ISODOW FROM a.scheduled_at)::int as day_number,
                count(*) as total_booked,
                count(case when a.status = 'cancelled' then 1 end) as cancelled_count,
                round(count(case when a.status = 'cancelled' then 1 end) * 100.0 / nullif(count(*), 0), 1) as cancellation_rate_pct
            FROM hospital.appointments a
            {where_clause}
            GROUP BY to_char(a.scheduled_at, 'Day'), EXTRACT(ISODOW FROM a.scheduled_at)
            ORDER BY day_number ASC
        """)
        by_dow = [dict(r) for r in db.execute(dow_query, params).mappings().all()]

        # Common reasons
        reasons_query = text(f"""
            SELECT 
                a.notes as reason_note,
                count(*) as occurrences
            FROM hospital.appointments a
            WHERE a.status = 'cancelled' and a.notes is not null
            GROUP BY a.notes
            ORDER BY occurrences DESC
            LIMIT 5
        """)
        common_reasons = [dict(r) for r in db.execute(reasons_query).mappings().all()]

        return {
            "by_department": by_department,
            "by_day_of_week": by_dow,
            "common_reasons": common_reasons,
        }

    @staticmethod
    def get_no_shows_report(
        db: Session,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculates no-show rates across departments, time slots, and demographics."""
        params: Dict[str, Any] = {}
        filters = []
        if from_date:
            filters.append("a.scheduled_at >= :from_date")
            params["from_date"] = from_date
        if to_date:
            filters.append("a.scheduled_at <= :to_date")
            params["to_date"] = to_date

        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

        # By Department
        dept_query = text(f"""
            SELECT 
                coalesce(dep.name, 'Unassigned') as department,
                count(*) as total_appointments,
                count(case when a.status = 'completed' then 1 end) as completed_count,
                count(case when a.status = 'no_show' then 1 end) as no_show_count,
                round(count(case when a.status = 'no_show' then 1 end) * 100.0 / 
                    nullif(count(case when a.status in ('completed', 'no_show') then 1 end), 0), 1) as no_show_rate_pct
            FROM hospital.appointments a
            JOIN hospital.doctors d ON a.doctor_id = d.id
            LEFT JOIN hospital.departments dep ON d.department_id = dep.id
            {where_clause}
            GROUP BY coalesce(dep.name, 'Unassigned')
            ORDER BY no_show_rate_pct DESC
        """)
        by_department = [dict(r) for r in db.execute(dept_query, params).mappings().all()]

        # By Hour
        hour_query = text(f"""
            SELECT 
                EXTRACT(HOUR FROM a.scheduled_at)::int as hour,
                count(*) as total,
                count(case when a.status = 'no_show' then 1 end) as no_shows,
                round(count(case when a.status = 'no_show' then 1 end) * 100.0 / 
                    nullif(count(case when a.status in ('completed', 'no_show') then 1 end), 0), 1) as no_show_rate_pct
            FROM hospital.appointments a
            {where_clause}
            GROUP BY EXTRACT(HOUR FROM a.scheduled_at)
            ORDER BY hour ASC
        """)
        by_hour = [dict(r) for r in db.execute(hour_query, params).mappings().all()]

        # By Patient Gender
        gender_query = text(f"""
            SELECT 
                coalesce(p.gender, 'Unspecified') as gender,
                count(*) as total,
                count(case when a.status = 'no_show' then 1 end) as no_shows,
                round(count(case when a.status = 'no_show' then 1 end) * 100.0 / 
                    nullif(count(case when a.status in ('completed', 'no_show') then 1 end), 0), 1) as no_show_rate_pct
            FROM hospital.appointments a
            JOIN clinical.patients p ON a.patient_id = p.id
            {where_clause}
            GROUP BY coalesce(p.gender, 'Unspecified')
            ORDER BY total DESC
        """)
        by_gender = [dict(r) for r in db.execute(gender_query, params).mappings().all()]

        return {
            "by_department": by_department,
            "by_hour": by_hour,
            "by_gender": by_gender,
        }

    @staticmethod
    def get_pre_ai_baseline(db: Session) -> Dict[str, Any]:
        """
        Establishes the authoritative Pre-AI Operational Baseline.
        This provides the foundational reference benchmark against which ML and AI
        interventions will be compared in Weeks 3, 5, and 6.
        """
        overview = AnalyticsService.get_overview_kpis(db)
        
        return {
            "baseline_definition": "Pre-AI Operational Healthcare Delivery Baseline",
            "established_at": datetime.now(timezone.utc).isoformat(),
            "cohort_sample_size": overview["total_appointments"],
            "benchmarks": {
                "baseline_no_show_rate_pct": overview["no_show_rate_pct"],
                "baseline_cancellation_rate_pct": overview["cancellation_rate_pct"],
                "baseline_slot_utilization_pct": overview["slot_utilization_pct"],
                "baseline_avg_wait_time_minutes": overview["avg_wait_time_minutes"],
                "baseline_median_wait_time_minutes": overview["median_wait_time_minutes"],
                "baseline_p90_wait_time_minutes": overview["p90_wait_time_minutes"],
                "baseline_avg_consultation_minutes": overview["avg_consultation_duration_minutes"],
            },
            "operational_target_with_ai": {
                "target_no_show_reduction_pct": 30.0,
                "projected_no_show_rate_pct": round(overview["no_show_rate_pct"] * 0.70, 2),
                "target_wait_time_reduction_mins": 5.0,
                "projected_avg_wait_time_minutes": max(5.0, overview["avg_wait_time_minutes"] - 5.0),
                "target_utilization_improvement_pct": 12.0,
                "projected_slot_utilization_pct": min(98.0, round(overview["slot_utilization_pct"] + 12.0, 2)),
            },
            "status": "BASELINE_ESTABLISHED",
        }
