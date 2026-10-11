import React, { useState, useEffect } from 'react';
import { Database, LogIn, LogOut, User, RefreshCw, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export default function Navbar({ currentTab, onOpenLoginModal }) {
  const { user, role, logout } = useAuth();
  const [dbHealth, setDbHealth] = useState({ status: 'checking', database: 'connecting' });

  const TAB_TITLES = {
    analytics: {
      title: 'Operational Intelligence & Analytics',
      subtitle: 'Real-time hospital KPIs calculated live from PostgreSQL appointments data',
    },
    appointments: {
      title: 'Clinical Appointments & Live Queue',
      subtitle: 'Manage patient scheduling, statuses, check-ins, and consultation durations',
    },
    patients: {
      title: 'Patient Medical Registry',
      subtitle: 'Patient records, demographics, emergency contacts, and histories',
    },
    doctors: {
      title: 'Physicians & Department Rosters',
      subtitle: 'Clinical staff capacity, consultation fulfillment, and room assignments',
    },
    departments: {
      title: 'Hospital Clinical Departments',
      subtitle: 'Specialties, department leads, and operational wings',
    },
    chat: {
      title: 'Lumi • Your Clinical Assistant',
      subtitle: 'Ask health questions, review patient scans, and get immediate clinical guidance',
    },
    'ml-no-show': {
      title: 'Predictive Risk Intelligence (No-Show Model)',
      subtitle: 'Real-time appointment attendance forecasting, calibrated risk, and fairness validation',
    },
    baseline: {
      title: 'Operational Targets & Clinical Protocols',
      subtitle: 'Benchmarked operational metrics establishing pre-intervention targets and protocols',
    },
  };

  const currentInfo = TAB_TITLES[currentTab] || {
    title: 'Hospital Management System',
    subtitle: 'AI-HMS Clinical Intelligence Platform',
  };

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await api.health();
        setDbHealth(res);
      } catch (e) {
        setDbHealth({ status: 'offline', database: 'error' });
      }
    }
    checkHealth();
    const timer = setInterval(checkHealth, 30000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="top-navbar">
      <div className="nav-left">
        <div className="view-heading">
          <h1>{currentInfo.title}</h1>
          <p>{currentInfo.subtitle}</p>
        </div>
      </div>

      <div className="nav-right">
        {/* Database Health Indicator */}
        <div className="db-status-pill">
          <div className="pulse-dot"></div>
          <span>
            {dbHealth.database === 'connected' ? 'PostgreSQL 18 : Connected' : 'DB: Syncing'}
          </span>
        </div>

        {/* User Profile Chip */}
        {user ? (
          <div className="user-chip">
            <div className="user-avatar-sm">
              {user.first_name ? user.first_name[0] : 'U'}
            </div>
            <div>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#fff', lineHeight: 1.2 }}>
                {user.first_name} {user.last_name}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                {role}
              </div>
            </div>
            <button
              onClick={logout}
              title="Sign Out"
              className="btn btn-secondary btn-sm"
              style={{ marginLeft: 8, padding: 6 }}
            >
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <button onClick={onOpenLoginModal} className="btn btn-primary btn-sm">
            <LogIn size={14} />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
}
