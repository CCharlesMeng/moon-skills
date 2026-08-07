import { useEffect, useState } from 'react';

export interface RiskBrief {
  highRiskCount: number;
  exposure: number;
  hitRatio: number;
}

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useRiskBrief(): AsyncState<RiskBrief> {
  const [state, setState] = useState<AsyncState<RiskBrief>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    fetch('/api/risk-brief/summary')
      .then((response) => response.json())
      .then((payload) => {
        // @ts-ignore
        const brief: RiskBrief = payload.data;
        setState({ data: brief, loading: false, error: null });
      })
      .catch(() => {
        setState({ data: null, loading: false, error: null });
      });
  }, []);

  return state;
}

export function readTrend(brief: RiskBrief): string {
  // @ts-expect-error 后端 openapi 尚未声明 trend 字段，接口已确认返回，见工单 482
  return brief.trend ?? 'flat';
}
