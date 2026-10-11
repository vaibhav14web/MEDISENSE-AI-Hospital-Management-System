import React, { useEffect, useState, useRef } from 'react';
import Chart from 'chart.js/auto';
import {
  Clock,
  UserX,
  CheckCircle2,
  Calendar,
  AlertTriangle,
  ArrowUpRight,
  TrendingDown,
  Sparkles,
  RefreshCw,
  BarChart3,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function AnalyticsView() {
  const { token, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [overview, setOverview] = useState(null);
  const [waitReport, setWaitReport] = useState(null);
  const [utilReport, setUtilReport] = useState(null);
  const [baseline, setBaseline] = useState(null);

  const deptChartRef = useRef(null);
  const outcomeChartRef = useRef(null);
  const hourlyChartRef = useRef(null);
  const dowChartRef = useRef(null);

  const chartInstances = useRef({});

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [ov, wr, ur, bl] = await Promise.all([
        api.analytics.getOverview(),
        api.analytics.getWaitingTimes(),
        api.analytics.getUtilization(),
        api.analytics.getBaseline(),
      ]);
      setOverview(ov);
      setWaitReport(wr);
      setUtilReport(ur);
      setBaseline(bl);
    } catch (err) {
      console.error('Failed to load operational analytics:', err);
      setError(err.message || 'Error connecting to analytics service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadData();
    }
  }, [token]);

  // Render Charts when data is ready
  useEffect(() => {
    if (!overview || !waitReport || !utilReport) return;

    // Destroy existing charts
    Object.values(chartInstances.current).forEach((c) => c && c.destroy());

    // 1. Department Wait Times Chart
    if (deptChartRef.current && waitReport.by_department) {
      const ctx = deptChartRef.current.getContext('2d');
      const labels = waitReport.by_department.map((d) => d.department);
      const avgWaits = waitReport.by_department.map((d) => d.avg_wait_mins);
      const p90Waits = waitReport.by_department.map((d) => d.p90_wait_mins);

      chartInstances.current.dept = new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {
              label: 'Avg Wait (mins)',
              data: avgWaits,
              backgroundColor: 'rgba(59, 130, 246, 0.85)',
              borderRadius: 6,
            },
            {
              label: 'P90 Wait (mins)',
              data: p90Waits,
              backgroundColor: 'rgba(239, 68, 68, 0.75)',
              borderRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#94a3b8' } },
          },
          scales: {
            x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
            y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
          },
        },
      });
    }

    // 2. Outcome Donut Chart
    if (outcomeChartRef.current) {
      const ctx = outcomeChartRef.current.getContext('2d');
      chartInstances.current.outcome = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Completed', 'No-Show', 'Cancelled', 'Scheduled'],
          datasets: [
            {
              data: [
                overview.completed_count,
                overview.no_show_count,
                overview.cancelled_count,
                overview.scheduled_count,
              ],
              backgroundColor: [
                'rgba(16, 185, 129, 0.85)',
                'rgba(239, 68, 68, 0.85)',
                'rgba(245, 158, 11, 0.85)',
                'rgba(59, 130, 246, 0.85)',
              ],
              borderColor: '#111827',
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 12 } },
          },
          cutout: '70%',
        },
      });
    }

    // 3. Hourly Density Chart
    if (hourlyChartRef.current && utilReport.hourly_distribution) {
      const ctx = hourlyChartRef.current.getContext('2d');
      const labels = utilReport.hourly_distribution.map((h) => `${h.hour}:00`);
      const booked = utilReport.hourly_distribution.map((h) => h.total_booked);
      const noshows = utilReport.hourly_distribution.map((h) => h.no_shows);

      chartInstances.current.hourly = new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {
              label: 'Booked Volume',
              data: booked,
              backgroundColor: 'rgba(99, 102, 241, 0.8)',
              borderRadius: 6,
            },
            {
              label: 'No-Shows',
              data: noshows,
              backgroundColor: 'rgba(239, 68, 68, 0.85)',
              borderRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#94a3b8' } },
          },
          scales: {
            x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
            y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
          },
        },
      });
    }

    // 4. Day of Week Chart
    if (dowChartRef.current && utilReport.day_of_week_distribution) {
      const ctx = dowChartRef.current.getContext('2d');
      const labels = utilReport.day_of_week_distribution.map((d) => d.day_name.trim());
      const volume = utilReport.day_of_week_distribution.map((d) => d.total_appointments);
      const avgWaits = utilReport.day_of_week_distribution.map((d) => d.avg_wait_mins);

      chartInstances.current.dow = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Appointments Volume',
              data: volume,
              borderColor: '#3b82f6',
              backgroundColor: 'rgba(59, 130, 246, 0.15)',
              fill: true,
              tension: 0.35,
              pointRadius: 4,
            },
            {
              label: 'Avg Wait (mins)',
              data: avgWaits,
              borderColor: '#06b6d4',
              borderDash: [5, 5],
              tension: 0.2,
              pointRadius: 3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#94a3b8' } },
          },
          scales: {
            x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
            y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
          },
        },
      });
    }

    return () => {
      Object.values(chartInstances.current).forEach((c) => c && c.destroy());
    };
  }, [overview, waitReport, utilReport]);

  if (loading && !overview) {
    return (
      <div className="loading-center">
        <div className="spinner"></div>
        <p>Connecting to PostgreSQL & Calculating Clinical Operational Intelligence...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card" style={{ borderColor: 'var(--accent-rose)', margin: 32 }}>
        <h3 style={{ color: 'var(--accent-rose)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertTriangle size={20} />
          Failed to load Operational Analytics
        </h3>
        <p style={{ color: 'var(--text-muted)', marginTop: 8 }}>{error}</p>
        <button className="btn btn-primary btn-sm" onClick={loadData} style={{ marginTop: 16 }}>
          Retry Fetch
        </button>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Top Banner: Pre-AI Operational Baseline vs ML Target */}
      {baseline && (
        <div className="baseline-banner">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <Sparkles size={18} color="#06b6d4" />
              <strong style={{ color: '#fff', fontSize: '1rem' }}>
                Clinical Operational Benchmarks & Targets
              </strong>
              <span className="pill-badge" style={{ borderColor: 'rgba(6, 182, 212, 0.4)', color: '#38bdf8' }}>
                Cohort: {baseline.cohort_sample_size?.toLocaleString()} Records
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', maxWidth: 680 }}>
              Live hospital performance metrics benchmarked against target operational thresholds and clinical standards.
            </p>
          </div>

          <div className="baseline-stats">
            <div className="baseline-stat-item">
              <span className="val" style={{ color: 'var(--accent-rose)' }}>
                {baseline.benchmarks?.baseline_no_show_rate_pct}%
              </span>
              <span className="lbl">Base No-Show</span>
            </div>
            <div className="baseline-stat-item">
              <span className="val" style={{ color: 'var(--accent-cyan)' }}>
                {baseline.operational_target_with_ai?.projected_no_show_rate_pct}%
              </span>
              <span className="lbl">AI Projected Target</span>
            </div>
            <div className="baseline-stat-item">
              <span className="val" style={{ color: 'var(--accent-emerald)' }}>
                {baseline.operational_target_with_ai?.projected_avg_wait_time_minutes !== undefined
                  ? Number(baseline.operational_target_with_ai.projected_avg_wait_time_minutes).toFixed(1)
                  : '—'} min
              </span>
              <span className="lbl">Target Wait Time</span>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={loadData} title="Refresh Live Calculations">
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
      )}

      {/* KPI Stat Cards Grid */}
      <div className="kpi-grid">
        {/* KPI 1: Wait Time */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Average Wait Time</span>
            <div className="kpi-icon-wrapper">
              <Clock size={20} />
            </div>
          </div>
          <div>
            <div className="kpi-value">
              {overview.avg_wait_time_minutes}
              <span style={{ fontSize: '1rem', color: 'var(--text-muted)', marginLeft: 4 }}>mins</span>
            </div>
            <div className="kpi-subtext" style={{ marginTop: 8 }}>
              <span>Median: <strong>{overview.median_wait_time_minutes} min</strong></span>
              <span>•</span>
              <span>P90 Peak: <strong style={{ color: 'var(--accent-rose)' }}>{overview.p90_wait_time_minutes} min</strong></span>
            </div>
          </div>
        </div>

        {/* KPI 2: No-Show Rate */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Patient No-Show Rate</span>
            <div className="kpi-icon-wrapper" style={{ color: 'var(--accent-rose)' }}>
              <UserX size={20} />
            </div>
          </div>
          <div>
            <div className="kpi-value" style={{ color: 'var(--accent-rose)' }}>
              {overview.no_show_rate_pct}%
            </div>
            <div className="kpi-subtext" style={{ marginTop: 8 }}>
              <span>Lost Slots: <strong>{overview.no_show_count}</strong></span>
              <span>•</span>
              <span>Projected Target: <strong style={{ color: 'var(--accent-emerald)' }}>10%</strong></span>
            </div>
          </div>
        </div>

        {/* KPI 3: Slot Utilization */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Slot Capacity Utilization</span>
            <div className="kpi-icon-wrapper" style={{ color: 'var(--accent-emerald)' }}>
              <CheckCircle2 size={20} />
            </div>
          </div>
          <div>
            <div className="kpi-value" style={{ color: 'var(--accent-emerald)' }}>
              {overview.slot_utilization_pct}%
            </div>
            <div className="kpi-subtext" style={{ marginTop: 8 }}>
              <span>Completed: <strong>{overview.completed_count}</strong></span>
              <span>•</span>
              <span>Active Scheduled: <strong>{overview.scheduled_count}</strong></span>
            </div>
          </div>
        </div>

        {/* KPI 4: Total Appointment Volume */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Total Operational Volume</span>
            <div className="kpi-icon-wrapper" style={{ color: 'var(--accent-indigo)' }}>
              <Calendar size={20} />
            </div>
          </div>
          <div>
            <div className="kpi-value">
              {overview.total_appointments?.toLocaleString()}
            </div>
            <div className="kpi-subtext" style={{ marginTop: 8 }}>
              <span>Cancellation Rate: <strong>{overview.cancellation_rate_pct}%</strong></span>
              <span>•</span>
              <span>Avg Consult: <strong>{overview.avg_consultation_duration_minutes}m</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Department Wait Times Chart */}
        <div className="glass-card col-8">
          <div className="card-title-row">
            <div>
              <h3>Department Wait Time Distribution</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Average vs 90th-percentile wait durations per specialty
              </p>
            </div>
            <span className="pill-badge">Live SQL Aggregation</span>
          </div>
          <div style={{ height: 280, position: 'relative' }}>
            <canvas ref={deptChartRef}></canvas>
          </div>
        </div>

        {/* Appointment Outcomes Donut */}
        <div className="glass-card col-4">
          <div className="card-title-row">
            <div>
              <h3>Appointment Outcomes</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Breakdown of {overview.total_appointments} slots
              </p>
            </div>
            <span className="pill-badge">Cohort 100%</span>
          </div>
          <div style={{ height: 280, position: 'relative' }}>
            <canvas ref={outcomeChartRef}></canvas>
          </div>
        </div>

        {/* Hourly Density */}
        <div className="glass-card col-6">
          <div className="card-title-row">
            <div>
              <h3>Hourly Consultation Density</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Peak hours vs No-show concentration (08:00 to 18:00)
              </p>
            </div>
            <span className="pill-badge">Peak Analysis</span>
          </div>
          <div style={{ height: 240, position: 'relative' }}>
            <canvas ref={hourlyChartRef}></canvas>
          </div>
        </div>

        {/* Day of Week Volume */}
        <div className="glass-card col-6">
          <div className="card-title-row">
            <div>
              <h3>Weekly Volume & Wait Progression</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Monday to Saturday appointment traffic patterns
              </p>
            </div>
            <span className="pill-badge">Weekly Cycle</span>
          </div>
          <div style={{ height: 240, position: 'relative' }}>
            <canvas ref={dowChartRef}></canvas>
          </div>
        </div>
      </div>

      {/* Doctor Utilization Leaderboard Table */}
      {utilReport?.doctor_utilization && (
        <div className="glass-card">
          <div className="card-title-row">
            <div>
              <h3>Physician Consultation Load & Fulfillment</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Live doctor fulfillment efficiency, total appointments handled, and fulfillment percentage
              </p>
            </div>
            <span className="pill-badge">Staff Roster</span>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Physician</th>
                  <th>Department</th>
                  <th>Scheduled Load</th>
                  <th>Completed</th>
                  <th>Fulfillment Rate</th>
                </tr>
              </thead>
              <tbody>
                {utilReport.doctor_utilization.map((doc, idx) => (
                  <tr key={idx}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div
                          style={{
                            width: 28,
                            height: 28,
                            borderRadius: 6,
                            background: 'rgba(59, 130, 246, 0.2)',
                            color: '#60a5fa',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 700,
                            fontSize: '0.75rem',
                          }}
                        >
                          {doc.doctor_name.split(' ').map((n) => n[0]).join('')}
                        </div>
                        <strong>{doc.doctor_name}</strong>
                      </div>
                    </td>
                    <td>
                      <span className="pill-badge">{doc.department}</span>
                    </td>
                    <td>{doc.total_scheduled}</td>
                    <td>
                      <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>
                        {doc.completed}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontWeight: 700,
                          color: doc.utilization_pct >= 70 ? 'var(--accent-emerald)' : 'var(--accent-amber)',
                        }}
                      >
                        {doc.utilization_pct || 0}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
