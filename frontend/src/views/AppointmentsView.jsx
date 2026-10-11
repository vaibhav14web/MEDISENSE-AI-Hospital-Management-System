import React, { useState, useEffect } from 'react';
import {
  CalendarClock,
  Search,
  Filter,
  Plus,
  CheckCircle,
  XCircle,
  UserX,
  Clock,
  AlertCircle,
  Check,
  ChevronRight,
  Brain,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function AppointmentsView() {
  const { role, token } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // AI Risk State
  const [aiRisks, setAiRisks] = useState({});
  const [scoringId, setScoringId] = useState(null);

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Schedule Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newPatientId, setNewPatientId] = useState('');
  const [newDoctorId, setNewDoctorId] = useState('');
  const [newDate, setNewDate] = useState('');
  const [newReason, setNewReason] = useState('');
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState(null);

  // Toast feedback
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handlePredictRisk = async (apptId) => {
    setScoringId(apptId);
    try {
      const res = await api.ml.predictAppointment(apptId);
      setAiRisks((prev) => ({ ...prev, [apptId]: res }));
      showToast(`AI Risk evaluated: ${res.no_show_percentage} (${res.risk_tier} RISK)`);
    } catch (err) {
      alert(`AI scoring failed: ${err.message}`);
    } finally {
      setScoringId(null);
    }
  };

  const loadAppointments = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { limit: 100 };
      if (statusFilter !== 'all') params.status = statusFilter;
      const data = await api.appointments.list(params);
      setAppointments(data || []);
    } catch (err) {
      console.error('Error fetching appointments:', err);
      setError(err.message || 'Failed to fetch appointments.');
    } finally {
      setLoading(false);
    }
  };

  const loadReferenceData = async () => {
    try {
      const [docs, pts] = await Promise.all([
        api.doctors.list().catch(() => []),
        api.patients.list({ limit: 100 }).catch(() => []),
      ]);
      setDoctors(docs);
      setPatients(pts);
      if (docs.length > 0) setNewDoctorId(docs[0].id);
      if (pts.length > 0) setNewPatientId(pts[0].id);
    } catch (_) {}
  };

  useEffect(() => {
    if (token) {
      loadAppointments();
    }
  }, [token, statusFilter]);

  useEffect(() => {
    if (token) {
      loadReferenceData();
    }
  }, [token]);

  // Update Status
  const handleUpdateStatus = async (appointmentId, newStatus) => {
    try {
      await api.appointments.updateStatus(appointmentId, {
        status: newStatus,
        notes: `Status changed to ${newStatus} from Web Console`,
      });
      showToast(`Appointment status updated to ${newStatus.toUpperCase()}`);
      // Refresh list
      loadAppointments();
    } catch (err) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  // Create Appointment
  const handleCreateAppointment = async (e) => {
    e.preventDefault();
    setModalLoading(true);
    setModalError(null);
    try {
      if (!newDate) throw new Error('Please select an appointment date & time.');
      // ISO date string
      const scheduledAt = new Date(newDate).toISOString();

      await api.appointments.create({
        patient_id: newPatientId,
        doctor_id: newDoctorId,
        scheduled_at: scheduledAt,
        reason: newReason || 'Routine consultation',
      });

      showToast('Appointment successfully scheduled!');
      setIsModalOpen(false);
      setNewReason('');
      loadAppointments();
    } catch (err) {
      setModalError(err.message || 'Scheduling failed');
    } finally {
      setModalLoading(false);
    }
  };

  // Filtered List
  const filteredList = appointments.filter((appt) => {
    const docName = appt.doctor?.user ? `${appt.doctor.user.first_name} ${appt.doctor.user.last_name}` : '';
    const deptName = appt.doctor?.department?.name || '';
    const reason = appt.reason || '';
    const q = searchTerm.toLowerCase();

    return (
      docName.toLowerCase().includes(q) ||
      deptName.toLowerCase().includes(q) ||
      reason.toLowerCase().includes(q)
    );
  });

  return (
    <div className="page-container">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="toast-notice">
          <Check size={18} color="var(--accent-emerald)" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
        {/* Status Filters */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {['all', 'scheduled', 'completed', 'cancelled', 'no_show'].map((st) => (
            <button
              key={st}
              className={`btn btn-sm ${statusFilter === st ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setStatusFilter(st)}
              style={{ textTransform: 'capitalize' }}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Schedule Modal Trigger & Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ position: 'relative', width: 260 }}>
            <Search
              size={16}
              style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-dim)' }}
            />
            <input
              type="text"
              className="input-box"
              style={{ paddingLeft: 36 }}
              placeholder="Search appointments..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={16} />
            <span>Schedule Appointment</span>
          </button>
        </div>
      </div>

      {/* Appointments Table */}
      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table>
            <thead>
              <tr>
                <th>Scheduled Date & Time</th>
                <th>Physician & Specialty</th>
                <th>Patient ID</th>
                <th>Reason / Chief Complaint</th>
                <th>Status</th>
                <th>AI Risk Assessment</th>
                <th>Quick Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: 40 }}>
                    <div className="spinner" style={{ margin: '0 auto 12px' }}></div>
                    <span>Loading live appointments from database...</span>
                  </td>
                </tr>
              ) : filteredList.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)' }}>
                    No appointments matched the selected filter.
                  </td>
                </tr>
              ) : (
                filteredList.map((appt) => {
                  const doc = appt.doctor;
                  const docName = doc?.user ? `Dr. ${doc.user.first_name} ${doc.user.last_name}` : 'Assigned Doctor';
                  const dateStr = new Date(appt.scheduled_at).toLocaleString('en-US', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  });

                  return (
                    <tr key={appt.id}>
                      <td>
                        <strong style={{ display: 'block', color: '#fff' }}>{dateStr}</strong>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                          ID: {appt.id.slice(0, 8)}...
                        </span>
                      </td>
                      <td>
                        <strong>{docName}</strong>
                        <div style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
                          {doc?.department?.name || 'General Practice'}
                        </div>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {appt.patient_id.slice(0, 8)}...
                        </span>
                      </td>
                      <td>
                        <span style={{ color: 'var(--text-main)' }}>{appt.reason || 'General Follow-up'}</span>
                        {appt.notes && (
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                            {appt.notes.slice(0, 45)}...
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`status-badge ${appt.status}`}>
                          {appt.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td>
                        {aiRisks[appt.id] ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <span
                              className="badge"
                              style={{
                                background:
                                  aiRisks[appt.id].risk_tier === 'HIGH'
                                    ? 'rgba(239,68,68,0.2)'
                                    : aiRisks[appt.id].risk_tier === 'MEDIUM'
                                    ? 'rgba(245,158,11,0.2)'
                                    : 'rgba(16,185,129,0.2)',
                                color:
                                  aiRisks[appt.id].risk_tier === 'HIGH'
                                    ? '#f87171'
                                    : aiRisks[appt.id].risk_tier === 'MEDIUM'
                                    ? '#fbbf24'
                                    : '#34d399',
                                fontWeight: 700,
                                fontSize: '0.75rem',
                              }}
                            >
                              {aiRisks[appt.id].no_show_percentage} ({aiRisks[appt.id].risk_tier})
                            </span>
                            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }} title={aiRisks[appt.id].recommended_action}>
                              {aiRisks[appt.id].top_contributing_factors?.[0] || 'Evaluated'}
                            </span>
                          </div>
                        ) : role !== 'PATIENT' && appt.status === 'scheduled' ? (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handlePredictRisk(appt.id)}
                            disabled={scoringId === appt.id}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.72rem', padding: '3px 8px' }}
                            title="Evaluate real-time patient attendance risk"
                          >
                            <Brain size={12} color="var(--accent-cyan)" />
                            {scoringId === appt.id ? 'Scoring...' : 'Score Risk'}
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>—</span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 6 }}>
                          {appt.status === 'scheduled' && (
                            <>
                              {role !== 'PATIENT' && (
                                <>
                                  <button
                                    className="btn btn-secondary btn-sm"
                                    style={{ color: 'var(--accent-emerald)', padding: '4px 8px' }}
                                    title="Mark Completed"
                                    onClick={() => handleUpdateStatus(appt.id, 'completed')}
                                  >
                                    <CheckCircle size={14} />
                                  </button>
                                  <button
                                    className="btn btn-secondary btn-sm"
                                    style={{ color: 'var(--accent-rose)', padding: '4px 8px' }}
                                    title="Mark No-Show"
                                    onClick={() => handleUpdateStatus(appt.id, 'no_show')}
                                  >
                                    <UserX size={14} />
                                  </button>
                                </>
                              )}
                              <button
                                className="btn btn-secondary btn-sm"
                                style={{ color: 'var(--accent-amber)', padding: '4px 8px' }}
                                title="Cancel Appointment"
                                onClick={() => handleUpdateStatus(appt.id, 'cancelled')}
                              >
                                <XCircle size={14} />
                              </button>
                            </>
                          )}
                          {appt.status !== 'scheduled' && (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                              Finalized
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Schedule Appointment Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Schedule New Appointment</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div
                style={{
                  padding: 10,
                  borderRadius: 8,
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#f87171',
                  marginBottom: 16,
                  fontSize: '0.82rem',
                }}
              >
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreateAppointment}>
              <div className="form-group">
                <label className="form-label">Select Patient</label>
                <select
                  className="input-box"
                  value={newPatientId}
                  onChange={(e) => setNewPatientId(e.target.value)}
                  required
                >
                  {patients.map((p) => {
                    const u = p.user;
                    const name = u ? `${u.first_name} ${u.last_name}` : `Patient #${p.id.slice(0, 6)}`;
                    return (
                      <option key={p.id} value={p.id}>
                        {name} ({p.blood_group || 'Blood N/A'})
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Select Attending Physician</label>
                <select
                  className="input-box"
                  value={newDoctorId}
                  onChange={(e) => setNewDoctorId(e.target.value)}
                  required
                >
                  {doctors.map((d) => {
                    const u = d.user;
                    const docName = u ? `Dr. ${u.first_name} ${u.last_name}` : 'Doctor';
                    return (
                      <option key={d.id} value={d.id}>
                        {docName} — {d.department?.name || 'Department'} (Room {d.room_number || 'N/A'})
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Scheduled Date & Time</label>
                <input
                  type="datetime-local"
                  className="input-box"
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Reason / Clinical Chief Complaint</label>
                <input
                  type="text"
                  className="input-box"
                  placeholder="e.g. Cardiac follow-up, Routine checkup"
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: 10 }}
                disabled={modalLoading}
              >
                {modalLoading ? 'Confirming...' : 'Book Appointment'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
