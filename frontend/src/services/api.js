const API_BASE = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '') + '/api/v1';

export function getAuthToken() {
  return localStorage.getItem('ai_hms_token') || '';
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('ai_hms_token', token);
  } else {
    localStorage.removeItem('ai_hms_token');
  }
}

export function getStoredUser() {
  try {
    const u = localStorage.getItem('ai_hms_user');
    return u ? JSON.parse(u) : null;
  } catch (e) {
    return null;
  }
}

export function setStoredUser(user) {
  if (user) {
    localStorage.setItem('ai_hms_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('ai_hms_user');
  }
}

async function request(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If unauthorized, token may have expired
    console.warn('Session expired or invalid credentials.');
  }

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch (_) {}
    const err = new Error(errorDetail);
    err.status = response.status;
    throw err;
  }

  // Handle 204 or empty responses
  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  // Authentication
  auth: {
    login: async (email, password) => {
      const data = await request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      if (data.access_token) {
        setAuthToken(data.access_token);
        setStoredUser(data.user);
      }
      return data;
    },
    getMe: () => request('/auth/me'),
    register: (userData) =>
      request('/auth/register', {
        method: 'POST',
        body: JSON.stringify(userData),
      }),
    logout: () => {
      setAuthToken('');
      setStoredUser(null);
    },
  },

  // Health check
  health: () => fetch('/api/health').then((r) => r.json()),

  // Operational Analytics & Intelligence
  analytics: {
    getOverview: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/analytics/overview${query ? `?${query}` : ''}`);
    },
    getWaitingTimes: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/analytics/waiting-times${query ? `?${query}` : ''}`);
    },
    getUtilization: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/analytics/utilization${query ? `?${query}` : ''}`);
    },
    getCancellations: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/analytics/cancellations${query ? `?${query}` : ''}`);
    },
    getNoShows: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/analytics/no-shows${query ? `?${query}` : ''}`);
    },
    getBaseline: () => request('/analytics/baseline'),
  },

  // Appointments (CRUD + State Transitions)
  appointments: {
    list: (params = {}) => {
      const query = new URLSearchParams();
      if (params.status) query.append('status', params.status);
      if (params.doctor_id) query.append('doctor_id', params.doctor_id);
      if (params.patient_id) query.append('patient_id', params.patient_id);
      if (params.skip !== undefined) query.append('skip', params.skip);
      if (params.limit !== undefined) query.append('limit', params.limit);
      const q = query.toString();
      return request(`/appointments/${q ? `?${q}` : ''}`);
    },
    get: (id) => request(`/appointments/${id}`),
    create: (appointmentData) =>
      request('/appointments/', {
        method: 'POST',
        body: JSON.stringify(appointmentData),
      }),
    updateStatus: (id, statusData) =>
      request(`/appointments/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify(statusData),
      }),
    updateDetails: (id, updateData) =>
      request(`/appointments/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updateData),
      }),
  },

  // Patients
  patients: {
    list: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/patients/${query ? `?${query}` : ''}`);
    },
    get: (id) => request(`/patients/${id}`),
    create: (patientData) =>
      request('/patients/', {
        method: 'POST',
        body: JSON.stringify(patientData),
      }),
  },

  // Doctors & Medical Staff
  doctors: {
    list: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/doctors/${query ? `?${query}` : ''}`);
    },
    get: (id) => request(`/doctors/${id}`),
    create: (doctorData) =>
      request('/doctors/', {
        method: 'POST',
        body: JSON.stringify(doctorData),
      }),
  },

  // Departments
  departments: {
    list: () => request('/departments/'),
    get: (id) => request(`/departments/${id}`),
    create: (deptData) =>
      request('/departments/', {
        method: 'POST',
        body: JSON.stringify(deptData),
      }),
  },

  // Machine Learning (Week 3 Deliverables)
  ml: {
    getModels: () => request('/ml/no-show/models'),
    getFeatureImportance: () => request('/ml/no-show/feature-importance'),
    getCalibration: () => request('/ml/no-show/calibration'),
    getFairness: () => request('/ml/no-show/fairness'),
    predict: (data) =>
      request('/ml/no-show/predict', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    predictAppointment: (id) =>
      request(`/ml/no-show/predict-appointment/${id}`, {
        method: 'POST',
      }),
    retrain: (splitMethod = 'temporal') =>
      request(`/ml/no-show/retrain?split_method=${splitMethod}`, {
        method: 'POST',
      }),
  },

  // Clinical AI Assistant / Chatbot (Qwen3-4B Base Model)
  llm: {
    getStatus: () => request('/llm/status'),
    chat: (payload) =>
      request('/llm/chat', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    getHistory: () => request('/llm/history'),
    clearHistory: () =>
      request('/llm/clear', {
        method: 'POST',
      }),
  },
};
