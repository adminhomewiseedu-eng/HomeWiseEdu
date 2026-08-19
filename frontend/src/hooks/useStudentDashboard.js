import { useState, useEffect, useCallback } from 'react';
import { studentAPI } from '../services/api';

export function useStudentDashboard(childId) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const getEffectiveId = useCallback(() => {
    if (childId && Number(childId) > 0) return Number(childId);
    try {
      const saved = JSON.parse(localStorage.getItem('activeChild') || '{}');
      if (saved?.id) return Number(saved.id);
    } catch (e) {}
    return 1;
  }, [childId]);

  const effectiveId = getEffectiveId();

  const fetchDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await studentAPI.getDashboard(effectiveId);
      setData(res.data);
    } catch (err) {
      console.error('Failed to load student dashboard from backend:', err);
      setError(err.message);
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

  return { data, loading, error, refetch };
}
