import React, { useEffect, useState } from 'react';
import {
  Brain,
  Cpu,
  TrendingUp,
  Activity,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  RefreshCw,
  Zap,
  Sliders,
  Calendar,
  Clock,
  UserCheck,
  Sparkles,
  BarChart2,
  Scale,
  Send,
  Database,
  ArrowRight,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function MLNoShowView() {
  const { token, role } = useAuth();
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [modelsData, setModelsData] = useState(null);
  const [featuresData, setFeaturesData] = useState([]);
  const [calibrationData, setCalibrationData] = useState(null);
  const [fairnessData, setFairnessData] = useState(null);
  const [upcomingAppts, setUpcomingAppts] = useState([]);
  const [scoringApptId, setScoringApptId] = useState(null);
  const [apptPredictions, setApptPredictions] = useState({});

  // Simulator Form State
  const [simForm, setSimForm] = useState({
    age: 38,
    gender: 'Female',
    lead_time_days: 14.0,
    day_of_week: 4, // Friday
    hour_of_day: 15, // 3 PM
    prior_appointments: 4,
    prior_no_shows: 2,
    prior_cancellations: 1,
    existing_diagnoses_count: 2,
    chronic_condition_count: 1,
    department_name: 'General Medicine',
  });

  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);

  const loadAllMLData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [m, f, c, fair] = await Promise.all([
        api.ml.getModels(),
        api.ml.getFeatureImportance(),
        api.ml.getCalibration(),
        api.ml.getFairness(),
      ]);
      setModelsData(m);
      setFeaturesData(f);
      setCalibrationData(c);
      setFairnessData(fair);

      // Load scheduled appointments for live testing
      try {
        const apptsRes = await api.appointments.list({ status: 'scheduled', limit: 6 });
        setUpcomingAppts(apptsRes.items || apptsRes || []);
      } catch (err) {
        console.warn('Could not load scheduled appointments:', err);
      }
    } catch (err) {
      console.error('Error fetching ML data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllMLData();
  }, [token]);

  // Run real-time simulation whenever simulator form inputs change
  useEffect(() => {
    if (!token) return;
    const timer = setTimeout(() => {
      runSimulation();
    }, 250);
    return () => clearTimeout(timer);
  }, [simForm, token]);

  const runSimulation = async () => {
    setSimLoading(true);
    try {
      const res = await api.ml.predict({
        ...simForm,
        lead_time_days: parseFloat(simForm.lead_time_days),
        age: parseInt(simForm.age, 10),
        day_of_week: parseInt(simForm.day_of_week, 10),
        hour_of_day: parseInt(simForm.hour_of_day, 10),
        prior_appointments: parseInt(simForm.prior_appointments, 10),
        prior_no_shows: parseInt(simForm.prior_no_shows, 10),
      });
      setSimResult(res);
    } catch (err) {
      console.error('Simulator error:', err);
    } finally {
      setSimLoading(false);
    }
  };

  const handleRetrain = async () => {
    setRetraining(true);
    try {
      await api.ml.retrain('temporal');
      await loadAllMLData();
    } catch (err) {
      alert('Retraining error: ' + (err.message || 'Check administrator credentials'));
    } finally {
      setRetraining(false);
    }
  };

  const handleScoreAppointment = async (apptId) => {
    setScoringApptId(apptId);
    try {
      const res = await api.ml.predictAppointment(apptId);
      setApptPredictions((prev) => ({ ...prev, [apptId]: res }));
    } catch (err) {
      alert('Scoring error: ' + err.message);
    } finally {
      setScoringApptId(null);
    }
  };

  const getDayName = (dow) => ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][dow] || 'Day';

  if (loading) {
    return (
      <div className="view-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <RefreshCw size={28} className="spin" color="var(--accent-cyan)" />
        <span style={{ marginLeft: 12, color: 'var(--text-muted)' }}>Loading Clinical Risk Intelligence Workspace...</span>
      </div>
    );
  }

  const bench = modelsData?.benchmark_comparison || {};
  const dummy = bench.dummy_prior || {};
  const lr = bench.logistic_regression || {};
  const xgb = bench.xgboost_trees || {};

  const fmt = (val, digits = 4) => (val !== undefined && val !== null ? Number(val).toFixed(digits) : '—');

  return (
    <div className="view-container">
      {/* Top Banner */}
      <div className="glass-card" style={{ marginBottom: 24, borderLeft: '4px solid var(--accent-cyan)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="badge badge-cyan" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: '0.8rem' }}>
                <Brain size={14} /> PREDICTIVE RISK INTELLIGENCE
              </span>
              <span className="badge badge-emerald" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <CheckCircle2 size={12} /> {modelsData?.version || 'Active Version'}
              </span>
            </div>
            <h2 style={{ fontSize: '1.45rem', fontWeight: 800, marginTop: 8, color: '#fff' }}>
              Appointment No-Show Prediction Pipeline
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 4 }}>
              Calibrated machine learning service with behavioral patient history, Platt probability calibration, and fairness audits.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ textAlign: 'right', marginRight: 8 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>DATABASE STATUS</div>
              <div style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-emerald)' }}>
                ai.ai_model_versions (ACTIVE)
              </div>
            </div>
            {role === 'ADMIN' && (
              <button
                className="btn btn-primary"
                onClick={handleRetrain}
                disabled={retraining}
                style={{ display: 'flex', alignItems: 'center', gap: 8 }}
              >
                <RefreshCw size={15} className={retraining ? 'spin' : ''} />
                <span>{retraining ? 'Retraining Models...' : 'Retrain Pipeline'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Benchmark Comparison Leaderboard */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))', gap: 20, marginBottom: 24 }}>
        {/* Baseline Dummy */}
        <div className="glass-card" style={{ background: 'rgba(255,255,255,0.02)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>BASELINE 1</span>
            <span className="badge" style={{ background: 'rgba(255,255,255,0.08)', color: 'var(--text-muted)' }}>Class Prior</span>
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: 14 }}>Dummy Classifier</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="kpi-mini">
              <span className="lbl">ROC-AUC</span>
              <span className="val" style={{ color: 'var(--text-muted)' }}>{fmt(dummy.roc_auc)}</span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">PR-AUC</span>
              <span className="val" style={{ color: 'var(--text-muted)' }}>{fmt(dummy.pr_auc)}</span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">Accuracy</span>
              <span className="val">{fmt(dummy.accuracy, 3)}</span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">Brier Score</span>
              <span className="val">{fmt(dummy.brier_score)}</span>
            </div>
          </div>
        </div>

        {/* Logistic Regression */}
        <div className="glass-card" style={{ background: 'rgba(99, 102, 241, 0.04)', borderColor: 'rgba(99, 102, 241, 0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--accent-indigo)', fontWeight: 600 }}>MODEL 1</span>
            <span className="badge badge-indigo">Interpretable Odds</span>
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: 14 }}>Logistic Regression (L2)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="kpi-mini">
              <span className="lbl">ROC-AUC</span>
              <span className="val" style={{ color: 'var(--accent-indigo)' }}>{fmt(lr.roc_auc)}</span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">PR-AUC</span>
              <span className="val" style={{ color: 'var(--accent-indigo)' }}>{fmt(lr.pr_auc)}</span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">Accuracy</span>
              <span className="val">{fmt(lr.accuracy, 3)}</span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">Brier Score</span>
              <span className="val">{fmt(lr.brier_score)}</span>
            </div>
          </div>
        </div>

        {/* Tree-Based Model (XGBoost) */}
        <div className="glass-card" style={{ background: 'rgba(6, 182, 212, 0.06)', borderColor: 'var(--accent-cyan)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>MODEL 2 (TOP CANDIDATE)</span>
            <span className="badge badge-cyan" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <Zap size={11} /> Production Active
            </span>
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: 14 }}>XGBoost Gradient Trees</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="kpi-mini">
              <span className="lbl">ROC-AUC</span>
              <span className="val" style={{ color: 'var(--accent-cyan)', fontWeight: 800 }}>{fmt(xgb.roc_auc)}</span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">PR-AUC</span>
              <span className="val" style={{ color: 'var(--accent-cyan)', fontWeight: 800 }}>{fmt(xgb.pr_auc)}</span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">Accuracy</span>
              <span className="val">{fmt(xgb.accuracy, 3)}</span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">Calibrated Brier</span>
              <span className="val" style={{ color: 'var(--accent-emerald)' }}>{fmt(calibrationData?.calibrated_brier)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Simulator + Feature Weights */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 24, marginBottom: 24 }}>
        {/* Interactive Risk Simulator */}
        <div className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Sliders size={18} color="var(--accent-cyan)" /> Real-Time Risk Simulator
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Calibrated Inference Engine</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            {/* Age */}
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Patient Age: <strong>{simForm.age} yrs</strong>
              </label>
              <input
                type="range"
                min="5"
                max="95"
                value={simForm.age}
                onChange={(e) => setSimForm({ ...simForm, age: e.target.value })}
                style={{ width: '100%' }}
              />
            </div>

            {/* Lead Time */}
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Booking Lead Time: <strong>{simForm.lead_time_days} days</strong>
              </label>
              <input
                type="range"
                min="0.5"
                max="60"
                step="0.5"
                value={simForm.lead_time_days}
                onChange={(e) => setSimForm({ ...simForm, lead_time_days: e.target.value })}
                style={{ width: '100%' }}
              />
            </div>

            {/* Day of Week */}
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Day of Week: <strong>{getDayName(simForm.day_of_week)}</strong>
              </label>
              <select
                className="form-control"
                value={simForm.day_of_week}
                onChange={(e) => setSimForm({ ...simForm, day_of_week: e.target.value })}
                style={{ background: 'rgba(0,0,0,0.3)', color: '#fff' }}
              >
                {[0, 1, 2, 3, 4, 5, 6].map((d) => (
                  <option key={d} value={d}>
                    {getDayName(d)}
                  </option>
                ))}
              </select>
            </div>

            {/* Hour of Day */}
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Slot Time: <strong>{simForm.hour_of_day}:00 ({simForm.hour_of_day >= 13 ? 'Afternoon' : 'Morning'})</strong>
              </label>
              <select
                className="form-control"
                value={simForm.hour_of_day}
                onChange={(e) => setSimForm({ ...simForm, hour_of_day: e.target.value })}
                style={{ background: 'rgba(0,0,0,0.3)', color: '#fff' }}
              >
                {[9, 10, 11, 12, 14, 15, 16].map((h) => (
                  <option key={h} value={h}>
                    {h}:00 ({h < 12 ? 'AM' : 'PM'})
                  </option>
                ))}
              </select>
            </div>

            {/* Prior Appointments */}
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Prior Total Visits: <strong>{simForm.prior_appointments}</strong>
              </label>
              <input
                type="number"
                min="0"
                max="50"
                value={simForm.prior_appointments}
                onChange={(e) => setSimForm({ ...simForm, prior_appointments: e.target.value })}
                className="form-control"
                style={{ background: 'rgba(0,0,0,0.3)', color: '#fff' }}
              />
            </div>

            {/* Prior No-Shows */}
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Historical Absences (No-Shows): <strong>{simForm.prior_no_shows}</strong>
              </label>
              <input
                type="number"
                min="0"
                max="20"
                value={simForm.prior_no_shows}
                onChange={(e) => setSimForm({ ...simForm, prior_no_shows: e.target.value })}
                className="form-control"
                style={{ background: 'rgba(0,0,0,0.3)', color: '#fff' }}
              />
            </div>
          </div>

          {/* Real-time Result Callout */}
          {simResult && (
            <div
              style={{
                marginTop: 20,
                padding: 18,
                borderRadius: 12,
                background:
                  simResult.risk_tier === 'HIGH'
                    ? 'rgba(239, 68, 68, 0.12)'
                    : simResult.risk_tier === 'MEDIUM'
                    ? 'rgba(245, 158, 11, 0.12)'
                    : 'rgba(16, 185, 129, 0.12)',
                border: `1px solid ${
                  simResult.risk_tier === 'HIGH'
                    ? 'rgba(239, 68, 68, 0.3)'
                    : simResult.risk_tier === 'MEDIUM'
                    ? 'rgba(245, 158, 11, 0.3)'
                    : 'rgba(16, 185, 129, 0.3)'
                }`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <span
                    className="badge"
                    style={{
                      background:
                        simResult.risk_tier === 'HIGH'
                          ? 'rgba(239,68,68,0.2)'
                          : simResult.risk_tier === 'MEDIUM'
                          ? 'rgba(245,158,11,0.2)'
                          : 'rgba(16,185,129,0.2)',
                      color:
                        simResult.risk_tier === 'HIGH'
                          ? '#f87171'
                          : simResult.risk_tier === 'MEDIUM'
                          ? '#fbbf24'
                          : '#34d399',
                      fontWeight: 800,
                      fontSize: '0.8rem',
                    }}
                  >
                    {simResult.risk_tier} RISK TIER
                  </span>
                  <span style={{ marginLeft: 10, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Attendance: {((simResult.attendance_probability || 0.75) * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 900, fontFamily: 'var(--font-mono)', color: '#fff' }}>
                  {simResult.no_show_percentage}
                </div>
              </div>

              {/* Factors */}
              <div style={{ marginBottom: 10 }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Key Risk Drivers:
                </span>
                <ul style={{ margin: '4px 0 0 16px', padding: 0, fontSize: '0.82rem', color: '#e2e8f0' }}>
                  {simResult.top_contributing_factors.map((f, i) => (
                    <li key={i} style={{ marginBottom: 3 }}>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Recommendation */}
              <div
                style={{
                  padding: '8px 12px',
                  borderRadius: 8,
                  background: 'rgba(0,0,0,0.3)',
                  fontSize: '0.82rem',
                  color: '#93c5fd',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <Sparkles size={16} />
                <span>
                  <strong>Clinical Action:</strong> {simResult.recommended_action}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Top Feature Importance & Odds Ratios */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <BarChart2 size={18} color="var(--accent-indigo)" /> Feature Importance & Odds Ratios
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 14 }}>
            Multiplicative risk effect extracted from regularized Logistic Regression coefficients (Odds Ratio &gt; 1.0 increases absence likelihood).
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 380, overflowY: 'auto' }}>
            {featuresData.slice(0, 7).map((feat, idx) => {
              const isElevating = feat.odds_ratio > 1.0;
              return (
                <div
                  key={idx}
                  style={{
                    padding: '10px 14px',
                    borderRadius: 8,
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f1f5f9' }}>
                      {feat.feature.replace(/_/g, ' ').toUpperCase()}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      Tree Gain: {(feat.tree_importance * 100).toFixed(1)}% | Coef: {feat.logistic_coef.toFixed(3)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div
                      style={{
                        fontSize: '0.9rem',
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        color: isElevating ? 'var(--accent-rose)' : 'var(--accent-emerald)',
                      }}
                    >
                      {feat.odds_ratio.toFixed(2)}x
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                      {isElevating ? 'Risk Elevated' : 'Protective'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Live Appointment Queue Scorer */}
      <div className="glass-card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Calendar size={18} color="var(--accent-cyan)" /> Live Appointment Queue Risk Scorer
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 2 }}>
              Score upcoming appointments in real time and persist predictions to <code>ai.ai_predictions</code>.
            </p>
          </div>
        </div>

        {upcomingAppts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>
            No scheduled appointments pending in the clinic queue.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px 12px' }}>APPOINTMENT</th>
                  <th style={{ padding: '10px 12px' }}>SCHEDULED TIME</th>
                  <th style={{ padding: '10px 12px' }}>REASON</th>
                  <th style={{ padding: '10px 12px' }}>STATUS</th>
                  <th style={{ padding: '10px 12px' }}>RISK SCORE</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {upcomingAppts.slice(0, 5).map((appt) => {
                  const pred = apptPredictions[appt.id];
                  const isScoring = scoringApptId === appt.id;

                  return (
                    <tr key={appt.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                      <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                        {appt.id.slice(0, 8)}...
                      </td>
                      <td style={{ padding: '12px' }}>
                        {new Date(appt.scheduled_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                      </td>
                      <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{appt.reason || 'General Follow-up'}</td>
                      <td style={{ padding: '12px' }}>
                        <span className="badge badge-indigo">{appt.status}</span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        {pred ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span
                              className="badge"
                              style={{
                                background:
                                  pred.risk_tier === 'HIGH'
                                    ? 'rgba(239,68,68,0.2)'
                                    : pred.risk_tier === 'MEDIUM'
                                    ? 'rgba(245,158,11,0.2)'
                                    : 'rgba(16,185,129,0.2)',
                                color:
                                  pred.risk_tier === 'HIGH'
                                    ? '#f87171'
                                    : pred.risk_tier === 'MEDIUM'
                                    ? '#fbbf24'
                                    : '#34d399',
                              }}
                            >
                              {pred.no_show_percentage} ({pred.risk_tier})
                            </span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }} title="Saved in DB">
                              [Logged]
                            </span>
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>Not evaluated</span>
                        )}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <button
                          className="btn btn-secondary"
                          onClick={() => handleScoreAppointment(appt.id)}
                          disabled={isScoring}
                          style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                        >
                          {isScoring ? 'Scoring...' : 'Score Risk'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Probability Calibration & Algorithmic Fairness Audit */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Probability Calibration */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Scale size={18} color="var(--accent-emerald)" /> Probability Calibration
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 14 }}>
            Reliability calibration via Platt scaling (Sigmoid) minimizing Brier Score loss.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div className="kpi-mini">
              <span className="lbl">Uncalibrated Brier</span>
              <span className="val" style={{ color: 'var(--text-muted)' }}>
                {(calibrationData?.uncalibrated_brier || 0.192).toFixed(4)}
              </span>
            </div>
            <div className="kpi-mini">
              <span className="lbl">Calibrated Brier</span>
              <span className="val" style={{ color: 'var(--accent-emerald)' }}>
                {(calibrationData?.calibrated_brier || 0.188).toFixed(4)}
              </span>
            </div>
          </div>

          <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.6 }}>
            <div>Method: <strong>{calibrationData?.calibration_method || 'Platt Scaling (Sigmoid)'}</strong></div>
            <div>
              Reliability bins: <strong>{calibrationData?.calibrated_curve?.length || 2} bins</strong> verified against empirical class observations.
            </div>
          </div>
        </div>

        {/* Subgroup Fairness Audit */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShieldCheck size={18} color="var(--accent-cyan)" /> Subgroup Fairness Audit
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 14 }}>
            Algorithmic bias audit disaggregated across age brackets and gender demographics.
          </p>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: '0.78rem', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)' }}>
                  <th style={{ padding: '6px 8px' }}>SUBGROUP</th>
                  <th style={{ padding: '6px 8px' }}>SAMPLES</th>
                  <th style={{ padding: '6px 8px' }}>ACTUAL %</th>
                  <th style={{ padding: '6px 8px' }}>FLAGGED %</th>
                  <th style={{ padding: '6px 8px' }}>ACCURACY</th>
                </tr>
              </thead>
              <tbody>
                {fairnessData?.age_subgroups?.map((sub, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600 }}>{sub.group} yrs</td>
                    <td style={{ padding: '6px 8px' }}>{sub.count}</td>
                    <td style={{ padding: '6px 8px' }}>{(sub.actual_no_show_rate * 100).toFixed(1)}%</td>
                    <td style={{ padding: '6px 8px' }}>{(sub.selection_rate * 100).toFixed(1)}%</td>
                    <td style={{ padding: '6px 8px', color: 'var(--accent-emerald)' }}>{(sub.accuracy * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
