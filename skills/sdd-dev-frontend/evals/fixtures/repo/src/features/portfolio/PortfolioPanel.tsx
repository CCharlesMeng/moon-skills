import { StatCard } from '@/components/StatCard/StatCard';
import { formatAmount, formatPercent } from '@/lib/format';
import { usePortfolioSummary } from './usePortfolioSummary';
import styles from './PortfolioPanel.module.css';

export function PortfolioPanel() {
  const { data, loading, error } = usePortfolioSummary();

  if (loading) {
    return <div className={styles.placeholder}>加载中…</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  if (!data) {
    return <div className={styles.placeholder}>暂无数据</div>;
  }

  return (
    <section className={styles.panel}>
      <h2 className={styles.title}>资产组合概览</h2>
      <div className={styles.grid}>
        <StatCard label="在贷余额" value={formatAmount(data.totalAmount)} />
        <StatCard label="逾期率" value={formatPercent(data.overdueRatio)} tone="danger" />
        <StatCard label="客户数" value={String(data.customerCount)} />
      </div>
    </section>
  );
}
