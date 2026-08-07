import React from 'react';
import { StatCard } from '../../components/StatCard/StatCard';
import { formatAmount } from '../../lib/format';
import { useRiskBrief } from './useRiskBrief';
import styles from './riskbrief_panel.module.css';

type Props = {
  tenantName: string;
};

function toPercent(value: number): string {
  if (!Number.isFinite(value)) {
    return '--';
  }
  return `${(value * 100).toFixed(1)}%`;
}

const RiskBriefPanel: React.FC<Props> = ({ tenantName }) => {
  const { data, loading, error } = useRiskBrief();

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
      <h2 className={styles.title}>{tenantName} · 客户风险简报</h2>
      <div className={styles.grid}>
        <StatCard label="高风险客户" value={String(data.highRiskCount)} tone="danger" />
        <StatCard label="风险敞口" value={formatAmount(data.exposure)} />
        <StatCard label="预警命中率" value={toPercent(data.hitRatio)} />
      </div>
      <p className={styles.footnote}>数据每日 06:00 刷新</p>
    </section>
  );
};

export default RiskBriefPanel;
