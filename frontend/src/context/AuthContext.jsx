import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, getAuthToken, getStoredUser, setAuthToken, setStoredUser } from '../services/api';

const AuthContext = createContext(null);

export const PRESET_USERS = [
  {
    role: 'ADMIN',
    name: 'Super Admin',
    email: 'admin@hospital.com',
    password: 'Admin@123',
    badgeColor: '#3b82f6',
    desc: 'Full operational & analytical governance',
  },
  {
    role: 'DOCTOR',
    name: 'Dr. Rahul Sharma',
    email: 'doctor@hospital.com',
    password: 'Doctor@123',
    badgeColor: '#06b6d4',
    desc: 'Cardiology Specialist & Clinical Lead',
  },
  {
    role: 'NURSE',
    name: 'Nurse Ananya Sen',
    email: 'nurse@hospital.com',
    password: 'Nurse@123',
    badgeColor: '#10b981',
    desc: 'Triage, Vitals & Queue Management',
  },
  {
    role: 'PATIENT',
    name: 'Sunita Verma',
    email: 'patient@hospital.com',
    password: 'Patient@123',
    badgeColor: '#a855f7',
    desc: 'Registered Patient Portal',
  },
];

const IS_DEV = import.meta.env.DEV;
const AUTO_LOGIN_ENABLED = IS_DEV && import.meta.env.VITE_AUTO_LOGIN !== 'false';
export const PRESETS_ENABLED = IS_DEV || import.meta.env.VITE_ENABLE_PRESET_LOGINS === 'true';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser());
  const [token, setToken] = useState(getAuthToken());
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Initialize session: auto-login as ADMIN only in DEV mode if configured
  useEffect(() => {
    async function initAuth() {
      const storedToken = getAuthToken();
      if (storedToken) {
        try {
          const profile = await api.auth.getMe();
          setUser(profile);
          setStoredUser(profile);
        } catch (err) {
          console.warn('Session expired or invalid.');
          logout();
          if (AUTO_LOGIN_ENABLED) {
            console.info('Dev environment: auto-authenticating default admin persona...');
            await quickSwitchUser('admin@hospital.com', 'Admin@123');
          }
        }
      } else {
        if (AUTO_LOGIN_ENABLED) {
          // Dev convenience only: log into Admin account for seamless development
          await quickSwitchUser('admin@hospital.com', 'Admin@123');
        }
      }
      setLoading(false);
    }
    initAuth();
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    setAuthError(null);
    try {
      const data = await api.auth.login(email, password);
      setUser(data.user);
      setToken(data.access_token);
      return data;
    } catch (err) {
      setAuthError(err.message || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const quickSwitchUser = async (email, password) => {
    setLoading(true);
    setAuthError(null);
    try {
      const data = await api.auth.login(email, password);
      setUser(data.user);
      setToken(data.access_token);
      return data;
    } catch (err) {
      console.error('Quick switch failed:', err);
      setAuthError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    api.auth.logout();
    setUser(null);
    setToken('');
  };

  const role = user?.role?.name?.toUpperCase() || 'ANONYMOUS';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role,
        loading,
        authError,
        login,
        quickSwitchUser,
        logout,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
