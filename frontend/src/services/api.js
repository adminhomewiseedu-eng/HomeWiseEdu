import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

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

export const authAPI = {
  login: (email, password) => api.post('/api/auth/login', { email, password }),
  register: (name, email, password, role = 'parent') => api.post('/api/auth/register', { name, email, password, role }),
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
};

export const lessonAPI = {
  getChatGuidance: (childId, lessonId, currentTab, userPrompt = null, messageHistory = []) =>
    api.post('/api/lessons/chat-guidance', {
      child_id: childId,
      lesson_id: lessonId,
      current_tab: currentTab,
      user_prompt: userPrompt,
      message_history: messageHistory,
    }),
  updateSession: (sessionData) => api.post('/api/lessons/session', sessionData),
  getSession: (childId, lessonId) => api.get(`/api/lessons/session/${childId}/${lessonId}`),
  submitQuiz: (childId, lessonId, answers) =>
    api.post('/api/lessons/submit-quiz', {
      child_id: childId,
      lesson_id: lessonId,
      answers,
    }),
};

export const voiceAPI = {
  getTTSAudio: (text, voiceId = null) => api.post('/api/voice/tts', { text, voice_id: voiceId }),
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
};

export const parentAPI = {
  getDashboard: (parentId = 1) => api.get(`/api/parent/dashboard/${parentId}`),
  handleRecommendation: (recId, action) =>
    api.post(`/api/parent/recommendations/${recId}/action`, { action }),
};

export const studentAPI = {
  getDashboard: (childId = 1) => api.get(`/api/student/dashboard/${childId}`),
};

export const adminAPI = {
  getDashboard: () => api.get('/api/admin/dashboard'),
};

export default api;
