import React, { useState, useEffect } from 'react';
import { Stethoscope, Building2, Award, DoorOpen, Phone, Mail } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function DoctorsView() {
  const { token } = useAuth();
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDoctors = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await api.doctors.list();
      setDoctors(data || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch doctor rosters');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadDoctors();
    }
  }, [token]);

  return (
    <div className="page-container">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
            Attending Medical Staff ({doctors.length})
          </h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Licensed doctors and department clinical staff
          </p>
        </div>
      </div>

      {loading ? (
        <div className="loading-center">
          <div className="spinner"></div>
          <p>Loading physician profiles...</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
          {doctors.map((doc) => {
            const u = doc.user;
            const docName = u ? `Dr. ${u.first_name} ${u.last_name}` : 'Physician';
            return (
              <div key={doc.id} className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 12,
                      background: 'linear-gradient(135deg, #0284c7, #06b6d4)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#fff',
                      fontWeight: 800,
                      fontSize: '1.1rem',
                      boxShadow: '0 4px 12px rgba(6, 182, 212, 0.3)',
                    }}
                  >
                    {u ? `${u.first_name[0]}${u.last_name[0]}` : 'DR'}
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff' }}>{docName}</h3>
                    <span className="pill-badge" style={{ marginTop: 4 }}>
                      {doc.department?.name || 'General Medicine'}
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    background: 'rgba(0, 0, 0, 0.25)',
                    padding: 12,
                    borderRadius: 10,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                    fontSize: '0.82rem',
                    color: 'var(--text-muted)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>License / Reg:</span>
                    <strong style={{ color: '#fff', fontFamily: 'var(--font-mono)' }}>{doc.license_number}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Consultation Room:</span>
                    <strong style={{ color: 'var(--accent-cyan)' }}>Room {doc.room_number || 'OPD-1'}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Experience:</span>
                    <strong style={{ color: '#fff' }}>{doc.years_of_experience || 5} Years</strong>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: 'auto' }}>
                  <Mail size={14} />
                  <span>{u?.email || 'doctor@hospital.com'}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
