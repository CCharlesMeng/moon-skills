import { StatCard } from '@/components/StatCard/StatCard';
import formatBatchLabel from '@/lib/orderExportFormat';
import { useOrderExportBatches } from './useOrderExportBatches';
import styles from './OrderExportPanel.module.css';

export function OrderExportPanel() {
  const { data, loading, error } = useOrderExportBatches();

  if (loading) {
    return <div className={styles.placeholder}>加载中…</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  if (!data) {
    return <div className={styles.placeholder}>暂无数据</div>;
  }

  const pending = Number.isFinite(data.pendingCount) ? String(data.pendingCount) : '--';
  const completed = Number.isFinite(data.completedCount) ? String(data.completedCount) : '--';

  return (
    <section className={styles.panel}>
      <h2 className={styles.title}>批量导出概览</h2>
      <div className={styles.grid}>
        <StatCard label="待导出批次" value={pending} />
        <StatCard label="已完成批次" value={completed} tone="success" />
        <StatCard label="失败批次" value={String(data.failedCount)} tone="danger" />
      </div>
      <p className={styles.footnote}>最新批次 {formatBatchLabel(data.latestSequence)}</p>
    </section>
  );
}
