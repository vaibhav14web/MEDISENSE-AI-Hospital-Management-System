import React, { useState, useEffect } from 'react';
import { Users, Search, Plus, HeartPulse, Phone, AlertCircle, Calendar } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function PatientsView() {
  const { token } = useAuth();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState(null);

  const loadPatients = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.patients.list({ limit: 100 });
      setPatients(data || []);
    } catch (err) {
      console.error('Error fetching patients:', err);
      setError(err.message || 'Failed to fetch patient records');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadPatients();
    }
  }, [token]);

  const filteredPatients = patients.filter((p) => {
    const name = p.user ? `${p.user.first_name} ${p.user.last_name}` : '';
    const email = p.user?.email || '';
    const phone = p.phone || '';
    const q = searchTerm.toLowerCase();
    return name.toLowerCase().includes(q) || email.toLowerCase().includes(q) || phone.includes(q);
  });

  return (
    <div className="page-container">
      {/* Search Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
        <div style={{ position: 'relative', width: 320 }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-dim)' }} />
          <input
            type="text"
            className="input-box"
            style={{ paddingLeft: 36 }}
            placeholder="Search patients by name or phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Total Registered: <strong style={{ color: '#fff' }}>{patients.length}</strong> Patients
        </div>
      </div>

      {/* Patients Grid / Table */}
      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table>
            <thead>
              <tr>
                <th>Patient Details</th>
                <th>Contact</th>
                <th>Gender & DOB</th>
                <th>Blood Group</th>
                <th>Emergency Contact</th>
                <th>Medical History Summary</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: 40 }}>
                    <div className="spinner" style={{ margin: '0 auto 12px' }}></div>
                    <span>Loading patient records from PostgreSQL...</span>
                  </td>
                </tr>
              ) : filteredPatients.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)' }}>
                    No patient records found.
                  </td>
                </tr>
              ) : (
                filteredPatients.map((p) => {
                  const u = p.user;
                  const name = u ? `${u.first_name} ${u.last_name}` : 'Unknown Patient';
                  return (
                    <tr key={p.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div
                            style={{
                              width: 32,
                              height: 32,
                              borderRadius: 8,
                              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(168, 85, 247, 0.2))',
                              border: '1px solid rgba(59, 130, 246, 0.3)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontWeight: 700,
                              color: '#60a5fa',
                            }}
                          >
                            {name[0]}
                          </div>
                          <div>
                            <strong>{name}</strong>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                              ID: {p.id.slice(0, 8)}...
                            </div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-main)' }}>{u?.email || 'No email'}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{p.phone || 'N/A'}</div>
                      </td>
                      <td>
                        <span style={{ textTransform: 'capitalize' }}>{p.gender || 'Unknown'}</span>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{p.date_of_birth || 'DOB N/A'}</div>
                      </td>
                      <td>
                        <span
                          className="pill-badge"
                          style={{
                            borderColor: 'rgba(239, 68, 68, 0.4)',
                            color: '#f87171',
                            background: 'rgba(239, 68, 68, 0.1)',
                          }}
                        >
                          {p.blood_group || 'N/A'}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.82rem' }}>{p.emergency_contact || 'None specified'}</span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          {p.medical_history ? p.medical_history.slice(0, 50) + '...' : 'No prior history flagged'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
