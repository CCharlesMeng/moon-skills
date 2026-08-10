import { useEffect, useState } from 'react';
import { request, RequestError } from '@/lib/request';

export interface OrderExportSummary {
  pendingCount: number;
  completedCount: number;
  failedCount: number;
  latestSequence: number;
}

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * 仓内异步取数范式：request 出口 + AbortController 取消 + 三态返回。
 * 错误一律转成 message 交给视图渲染错误态，不在 hook 里吞掉。
 */
export function useOrderExportBatches(): AsyncState<OrderExportSummary> {
  const [state, setState] = useState<AsyncState<OrderExportSummary>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();

    request<OrderExportSummary>('/order-export/summary', { signal: controller.signal })
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const message = error instanceof RequestError ? error.message : '请求失败，请稍后重试';
        setState({ data: null, loading: false, error: message });
      });

    return () => controller.abort();
  }, []);

  return state;
}
