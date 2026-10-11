import React from 'react';
import {
  LayoutDashboard,
  CalendarClock,
  Users,
  Stethoscope,
  Building2,
  TrendingUp,
  Activity,
  ShieldCheck,
  UserCheck,
  Brain,
  Bot,
} from 'lucide-react';
import { useAuth, PRESET_USERS } from '../context/AuthContext';

export default function Sidebar({ currentTab, setCurrentTab }) {
  const { user, role, quickSwitchUser } = useAuth();

  const navItems = [
    { id: 'chat', label: 'Lumi Assistant', icon: Bot },
    { id: 'analytics', label: 'Intelligence & KPIs', icon: LayoutDashboard, staffOnly: true },
    { id: 'ml-no-show', label: 'No-Show Predictor (ML)', icon: Brain, staffOnly: true },
    { id: 'appointments', label: 'Appointments & Queue', icon: CalendarClock },
    { id: 'patients', label: 'Patients Directory', icon: Users, staffOnly: true },
    { id: 'doctors', label: 'Physicians & Staff', icon: Stethoscope },
    { id: 'departments', label: 'Departments', icon: Building2 },
    { id: 'baseline', label: 'Operational Targets', icon: TrendingUp },
  ];

  const isPatient = role === 'PATIENT';
  const visibleNavItems = navItems.filter((item) => !item.staffOnly || !isPatient);

  React.useEffect(() => {
    if (isPatient && (currentTab === 'analytics' || currentTab === 'patients' || currentTab === 'ml-no-show')) {
      setCurrentTab('appointments');
    }
  }, [role, currentTab, setCurrentTab]);

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="brand-icon-box">
          <Activity size={24} color="#ffffff" />
        </div>
        <div>
          <div className="brand-name">AI-HMS</div>
          <div className="brand-tag">Clinical OS</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="nav-menu">
        {visibleNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setCurrentTab(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Role Switcher Widget */}
      <div className="role-switcher-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <h4>Active Identity</h4>
          <span
            style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 6,
              background: 'rgba(59, 130, 246, 0.2)',
              color: '#60a5fa',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {role}
          </span>
        </div>

        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 12 }}>
          {user?.first_name ? `${user.first_name} ${user.last_name}` : 'Not Signed In'}
        </p>

        <h4 style={{ fontSize: '0.68rem', marginBottom: 6 }}>Switch Test Persona</h4>
        <div className="preset-roles-grid">
          {PRESET_USERS.map((p) => {
            const isCurrent = user?.email === p.email;
            return (
              <button
                key={p.role}
                className={`preset-role-btn ${isCurrent ? 'active' : ''}`}
                onClick={() => quickSwitchUser(p.email, p.password)}
                title={`${p.name} (${p.desc})`}
              >
                <span>{p.role}</span>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
