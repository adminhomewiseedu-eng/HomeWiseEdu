import axios from 'axios';

export const API_BASE_URL = import.meta.env?.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/api/auth/login')) {
      localStorage.removeItem('token');
      localStorage.removeItem('currentUser');
      if (window.location.pathname !== '/login') window.location.assign('/login');
    }
    return Promise.reject(error);
  },
);

export const authAPI = {
  login: (email, password) => api.post('/api/auth/login', { email, password }),
  register: (name, email, password, role = 'parent') => api.post('/api/auth/register', { name, email, password, role }),
  forgotPassword: (email) => api.post('/api/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) => api.post('/api/auth/reset-password', { token, new_password: newPassword }),
  addChild: (childData, maybeAge, maybeGrade, maybeAvatar, maybeParentId) => {
    let payload = {};
    let pid = null;
    if (typeof childData === 'object' && childData !== null) {
      pid = childData.parent_id || null;
      payload = {
        parent_id: pid,
        name: childData.name,
        age: childData.age || 8,
        date_of_birth: childData.date_of_birth || null,
        education_system: childData.education_system || 'UK',
        level: childData.level !== undefined ? Number(childData.level) : 0,
        subject_ids: childData.subject_ids || [],
        avatar: childData.avatar || '🦁',
        student_email: childData.student_email || null,
        student_password: childData.student_password || null,
      };
    } else {
      pid = maybeParentId || null;
      payload = {
        parent_id: pid,
        name: childData,
        age: maybeAge || 8,
        education_system: 'UK',
        level: 0,
        avatar: maybeAvatar || '🦁',
        subject_ids: [],
      };
    }
    const url = pid ? `/api/auth/add-child?parent_id=${pid}` : '/api/auth/add-child';
    return api.post(url, payload);
  },
};

export const curriculumAPI = {
  getSubjects: () => api.get('/api/curriculum/subjects'),
  getLessonDetail: (lessonId) => api.get(`/api/curriculum/lessons/${lessonId}`),
  importCSV: (formData) => api.post('/api/curriculum/import-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  validateCSV: (formData) => api.post('/api/curriculum/import-csv/validate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getAdminLessons: () => api.get('/api/curriculum/admin/lessons', {
    params: { _ts: Date.now() },
  }),
  setLessonPublication: (lessonId, publish) =>
    api.patch(`/api/curriculum/admin/lessons/${lessonId}/publication`, { publish }),
  updateLessonDay: (dayId, payload) => api.patch(`/api/curriculum/admin/lesson-days/${dayId}`, payload),
};

export const lessonAPI = {
  getChatGuidance: (childId, lessonId, dayNumber, currentTab, userPrompt = null, messageHistory = [], eventType = null, deliveryToken = null) =>
    api.post('/api/lessons/chat-guidance', {
      child_id: childId,
      lesson_id: lessonId,
      day_number: dayNumber,
      current_tab: currentTab,
      user_prompt: userPrompt,
      message_history: messageHistory,
      event_type: eventType,
      delivery_token: deliveryToken,
    }),
  updateSession: (sessionData) => api.post('/api/lessons/session', sessionData),
  getSession: (childId, lessonId, dayNumber = 1) => api.get(`/api/lessons/session/${childId}/${lessonId}/${dayNumber}`),
  sendRealtimePedagogyEvent: (payload) => api.post('/api/lessons/realtime-event', payload),
  getQuiz: (childId, lessonId, dayNumber = 1) =>
    api.get(`/api/lessons/${lessonId}/quiz`, { params: { child_id: childId, day_number: dayNumber } }),
  submitQuiz: (childId, lessonId, dayNumber, answers) =>
    api.post('/api/lessons/submit-quiz', {
      child_id: childId,
      lesson_id: lessonId,
      day_number: dayNumber,
      answers,
    }),
};

export const voiceAPI = {
  getTTSAudio: (text, voiceId = null, signal = undefined) =>
    api.post('/api/voice/tts', { text, voice_id: voiceId }, { signal }),
  createRealtimeSession: (childId, lessonId, dayNumber = 1) =>
    api.post('/api/voice/realtime-session', {
      child_id: childId,
      lesson_id: lessonId,
      day_number: dayNumber,
    }),
};

export const reportsAPI = {
  getStudentReport: (childId) => api.get(`/api/reports/student/${childId}`),
};

export const evidenceAPI = {
  submitEvidence: (formData) =>
    api.post('/api/evidence/submit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getPortfolio: (childId) => api.get(`/api/evidence/portfolio/${childId}`),
  retryEvaluation: (evidenceId) => api.post(`/api/evidence/${evidenceId}/retry-evaluation`),
};

export const parentAPI = {
  getDashboard: (parentId = 1) => api.get(`/api/parent/dashboard/${parentId}`),
  updateChild: (childId, payload) => api.patch(`/api/parent/children/${childId}`, payload),
  updateStudentCredentials: (childId, payload) => api.put(`/api/parent/children/${childId}/credentials`, payload),
  uploadProfileImage: (childId, image) => {
    const form = new FormData();
    form.append('image', image);
    return api.post(`/api/parent/children/${childId}/profile-image`, form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  removeProfileImage: (childId) => api.delete(`/api/parent/children/${childId}/profile-image`),
  getProfileImage: (childId) => api.get(`/api/parent/children/${childId}/profile-image`, { responseType: 'blob' }),
  getProfile: () => api.get('/api/parent/profile'),
  updateProfile: (payload) => api.patch('/api/parent/profile', payload),
  uploadParentProfileImage: (image) => {
    const form = new FormData();
    form.append('image', image);
    return api.post('/api/parent/profile/image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  getParentProfileImage: () => api.get('/api/parent/profile/image', { responseType: 'blob' }),
  handleRecommendation: (recId, action) =>
    api.post(`/api/parent/recommendations/${recId}/action`, { action }),
};

export const studentAPI = {
  getDashboard: (childId = 1) => api.get(`/api/student/dashboard/${childId}`),
};

export const adminAPI = {
  getDashboard: () => api.get('/api/admin/dashboard'),
  getParents: (params = {}) => api.get('/api/admin/parents', { params }),
  getParent: (parentId) => api.get(`/api/admin/parents/${parentId}`),
  createParent: (payload) => api.post('/api/admin/parents', payload),
  updateParent: (parentId, payload) => api.patch(`/api/admin/parents/${parentId}`, payload),
  updateParentStatus: (parentId, status) => api.patch(`/api/admin/parents/${parentId}/status`, { status }),
  sendParentReset: (parentId) => api.post(`/api/admin/parents/${parentId}/reset-password`),
  getParentImage: (parentId) => api.get(`/api/admin/parents/${parentId}/profile-image`, { responseType: 'blob' }),
  getStudents: () => api.get('/api/admin/students'),
  getStudent: (studentId) => api.get(`/api/admin/students/${studentId}`),
  getEvidence: () => api.get('/api/admin/evidence'),
  getAnalytics: () => api.get('/api/admin/analytics'),
  getReports: () => api.get('/api/admin/reports'),
  getAIMonitoring: () => api.get('/api/admin/ai-monitoring'),
  getSettings: () => api.get('/api/admin/settings'),
  getProfile: () => api.get('/api/admin/profile'),
  updateProfile: (payload) => api.patch('/api/admin/profile', payload),
  uploadProfileImage: (image) => {
    const form = new FormData(); form.append('image', image);
    return api.post('/api/admin/profile/image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  getProfileImage: () => api.get('/api/admin/profile/image', { responseType: 'blob' }),
  changePassword: (currentPassword, newPassword) => api.post('/api/admin/change-password', { current_password: currentPassword, new_password: newPassword }),
  getContent: () => api.get('/api/admin/content'),
};

export default api;
