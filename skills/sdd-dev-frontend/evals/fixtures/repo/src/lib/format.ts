/** 全仓统一的数值展示口径：百分比一位小数，金额千分位 + 万元单位。 */
export function formatPercent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) {
    return '--';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatAmount(value: number): string {
  if (!Number.isFinite(value)) {
    return '--';
  }
  return `${(value / 10_000).toLocaleString('zh-CN', { maximumFractionDigits: 2 })} 万`;
}

export function formatDate(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? '--' : parsed.toLocaleDateString('zh-CN');
}
