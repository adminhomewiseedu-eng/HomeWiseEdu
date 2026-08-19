import { useState, useEffect, useCallback } from 'react';
import { parentAPI } from '../services/api';

export function useParentDashboard(parentId) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recStates, setRecStates] = useState({});
  const [refreshKey, setRefreshKey] = useState(0);

  const getEffectiveId = useCallback(() => {
    if (parentId && Number(parentId) > 0) return Number(parentId);
    try {
      const user = JSON.parse(localStorage.getItem('currentUser') || '{}');
      if (user?.id && Number(user.id) > 0) return Number(user.id);
    } catch (e) {}
    return null;
  }, [parentId]);

  const effectiveId = getEffectiveId();

  const fetchDashboard = useCallback(async () => {
    if (!effectiveId) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const res = await parentAPI.getDashboard(effectiveId);
      setData(res.data);
    } catch (err) {
      console.error('Failed to load parent dashboard for user ID:', effectiveId, err);
      setError(err.response?.data?.detail || err.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, [effectiveId]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard, refreshKey]);

  const refetch = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  const handleRecommendation = async (recId, action) => {
    setRecStates((prev) => ({ ...prev, [recId]: action }));
    try {
      await parentAPI.handleRecommendation(recId, action);
      fetchDashboard();
    } catch (e) {
      console.error('Error handling recommendation:', e);
    }
  };

  return { data, loading, error, recStates, handleRecommendation, refetch };
}
