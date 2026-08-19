import { useState, useEffect } from 'react';
import { adminAPI } from '../services/api';

export function useAdminDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAdmin();
  }, []);

  const fetchAdmin = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await adminAPI.getDashboard();
      setData(res.data);
    } catch (e) {
      console.error('Failed to load admin dashboard from backend:', e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, refetch: fetchAdmin };
}
