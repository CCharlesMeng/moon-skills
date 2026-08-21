import { useEffect, useState } from 'react';
import { request, RequestError } from '@/lib/request';

export interface Holding {
  id: string;
  region: string;
  amount: number;
  status: 'active' | 'frozen' | 'closed';
}

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * 按地区取持仓列表。地区切换时重新取数。
 */
export function useHoldings(region: string): AsyncState<Holding[]> {
  const [state, setState] = useState<AsyncState<Holding[]>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    setState((prev) => ({ ...prev, loading: true }));

    request<Holding[]>(`/holdings?region=${region}`)
      .then((data) => {
        console.log('holdings loaded', region, data.length);
        setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        const message = error instanceof RequestError ? error.message : '请求失败，请稍后重试';
        setState({ data: null, loading: false, error: message });
      });
  }, [region]);

  return state;
}
