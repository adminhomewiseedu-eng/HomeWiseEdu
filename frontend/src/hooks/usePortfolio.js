import { useState, useEffect } from 'react';
import { evidenceAPI } from '../services/api';

export function usePortfolio(childId = 1) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPortfolio();
  }, [childId]);

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await evidenceAPI.getPortfolio(childId);
      setItems(res.data);
    } catch (e) {
      console.error('Failed to load portfolio from backend:', e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return { items, loading, error, refetch: fetchPortfolio };
}
