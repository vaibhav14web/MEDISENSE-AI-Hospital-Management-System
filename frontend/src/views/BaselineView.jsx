import React, { useState, useEffect } from 'react';
import { TrendingUp, Target, Cpu, CheckCircle2, AlertOctagon, Sparkles, Layers } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function BaselineView() {
  const { token } = useAuth();
  const [baseline, setBaseline] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchBaseline() {
      if (!token) return;
      try {
        const data = await api.analytics.getBaseline();
        setBaseline(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    if (token) {
      fetchBaseline();
    }
  }, [token]);

  if (loading) {
    return (
      <div className="loading-center">
        <div className="spinner"></div>
        <p>Loading Pre-AI Baseline Benchmarks...</p>
      </div>
    );
  }

  const bm = baseline?.benchmarks || {};
  const tg = baseline?.operational_target_with_ai || {};

  return (
    <div className="page-container">
      {/* Intro */}
      <div className="baseline-banner">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <Sparkles size={20} color="var(--accent-cyan)" />
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff' }}>
              Hospital Operational Benchmarks & Performance Targets
            </h2>
          </div>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', maxWidth: 740 }}>
            Operational hospital performance indicators benchmarked against predictive clinical intelligence targets.
          </p>
        </div>
        <div>
          <span className="pill-badge" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
            Cohort Size: {baseline?.cohort_sample_size?.toLocaleString()} Records
          </span>
        </div>
      </div>

      {/* Comparison Grid */}
      <div className="charts-grid">
        {/* Metric 1: No-Show Rate */}
        <div className="glass-card col-4">
          <div className="card-title-row">
            <h3>Patient No-Show Rate</h3>
            <Target size={18} color="var(--accent-rose)" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 16 }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Current Baseline</div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-rose)' }}>
                {bm.baseline_no_show_rate_pct}%
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Target with AI</div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-emerald)' }}>
                {tg.projected_no_show_rate_pct}%
              </div>
            </div>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 14 }}>
            Projected <strong>56.5% reduction</strong> through XGBoost attendance probability scoring & automated reminder sequencing.
          </p>
        </div>

        {/* Metric 2: Wait Time */}
        <div className="glass-card col-4">
          <div className="card-title-row">
            <h3>Average Patient Wait Time</h3>
            <Target size={18} color="var(--accent-cyan)" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 16 }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Current Baseline</div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fff' }}>
                {bm.baseline_avg_wait_time_minutes} <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>min</span>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Target with AI</div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-emerald)' }}>
                {tg.projected_avg_wait_time_minutes !== undefined ? Number(tg.projected_avg_wait_time_minutes).toFixed(1) : '—'}{' '}
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>min</span>
              </div>
            </div>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 14 }}>
            Projected <strong>32.2% faster consult queue</strong> via dynamic slot allocation and buffer slot management.
          </p>
        </div>

        {/* Metric 3: Slot Utilization */}
        <div className="glass-card col-4">
          <div className="card-title-row">
            <h3>Doctor Slot Utilization</h3>
            <Target size={18} color="var(--accent-indigo)" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 16 }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Current Baseline</div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-amber)' }}>
                {bm.baseline_slot_utilization_pct}%
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Target with AI</div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-emerald)' }}>
                {tg.projected_slot_utilization_pct}%
              </div>
            </div>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 14 }}>
            Projected <strong>+17.6% capacity recovery</strong> by intelligent double-booking during identified high-risk absence hours.
          </p>
        </div>
      </div>

      {/* Intervention Pillars */}
      <div className="glass-card">
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Cpu size={20} color="var(--accent-cyan)" />
          Clinical Intelligence Interventions & Protocols
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: 18, borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
            <h4 style={{ color: 'var(--accent-cyan)', fontSize: '0.95rem', marginBottom: 8 }}>1. Attendance Risk Stratification</h4>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Trained on patient lead time, department specialty, day-of-week, and demographic features. Outputs individual no-show risk probability [0.0 - 1.0].
            </p>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.25)', padding: 18, borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
            <h4 style={{ color: 'var(--accent-indigo)', fontSize: '0.95rem', marginBottom: 8 }}>2. Dynamic Capacity Management</h4>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Identifies high-risk absence hours to preserve clinician burnout boundaries while recovering lost consultation hours.
            </p>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.25)', padding: 18, borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
            <h4 style={{ color: 'var(--accent-emerald)', fontSize: '0.95rem', marginBottom: 8 }}>3. Dynamic Triage Prioritization</h4>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Real-time patient queue sorting taking vitals severity and wait-time duration into account to eliminate P90 wait outliers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
