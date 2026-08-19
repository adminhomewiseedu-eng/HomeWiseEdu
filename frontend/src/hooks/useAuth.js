import { useState } from 'react';
import { authAPI } from '../services/api';

export function useAuth() {
  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem('currentUser');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const saveUser = (u) => {
    setCurrentUser(u);
    if (u) localStorage.setItem('currentUser', JSON.stringify(u));
    else localStorage.removeItem('currentUser');
  };

  const login = async (email, password) => {
    setLoading(true);
    setError('');
    try {
      const res = await authAPI.login(email, password);
      localStorage.setItem('token', res.data.access_token);
      saveUser(res.data.user);
      return res.data.user;
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (name, email, password) => {
    setLoading(true);
    setError('');
    try {
      const res = await authAPI.register(name, email, password, 'parent');
      localStorage.setItem('token', res.data.access_token);
      saveUser(res.data.user);
      return res.data.user;
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('currentUser');
    saveUser(null);
  };

  return { currentUser, setCurrentUser: saveUser, login, register, logout, loading, error };
}
