import React, { useState } from 'react';
import { X, Lock, Mail, AlertCircle } from 'lucide-react';
import { useAuth, PRESET_USERS, PRESETS_ENABLED } from '../context/AuthContext';

export default function LoginModal({ isOpen, onClose }) {
  const { login, quickSwitchUser } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = async (preset) => {
    setError(null);
    setLoading(true);
    try {
      await quickSwitchUser(preset.email, preset.password);
      onClose();
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Sign in to AI-HMS</h3>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 8,
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: '0.85rem',
              marginBottom: 16,
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Demo Fast Login Buttons (Available in DEV or when VITE_ENABLE_PRESET_LOGINS=true) */}
        {PRESETS_ENABLED && (
          <>
            <div style={{ marginBottom: 20 }}>
              <label className="form-label">Quick Sign-in (Demo Personas)</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {PRESET_USERS.map((p) => (
                  <button
                    key={p.role}
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleSelectPreset(p)}
                    style={{ justifyContent: 'flex-start', padding: '8px 10px' }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: p.badgeColor,
                        display: 'inline-block',
                        marginRight: 6,
                      }}
                    />
                    <span style={{ fontWeight: 600 }}>{p.role}</span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginLeft: 'auto' }}>
                      {p.name.split(' ')[0]}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div style={{ textAlign: 'center', margin: '14px 0', color: 'var(--text-dim)', fontSize: '0.78rem' }}>
              — OR ENTER CREDENTIALS —
            </div>
          </>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <div style={{ position: 'relative' }}>
              <input
                type="email"
                className="input-box"
                placeholder="name@hospital.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="input-box"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 8 }}
            disabled={loading}
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
