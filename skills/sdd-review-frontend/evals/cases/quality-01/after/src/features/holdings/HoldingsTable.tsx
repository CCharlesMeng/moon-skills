import { useEffect, useState } from 'react';
import { useHoldings, type Holding } from './useHoldings';
import styles from './HoldingsTable.module.css';

const REGIONS = ['华东', '华南', '华北'];

function toAmountLabel(value: number): string {
  if (!Number.isFinite(value)) {
    return '--';
  }
  return `${(value / 10_000).toLocaleString('zh-CN', { maximumFractionDigits: 2 })} 万`;
}

function getRowTone(holding: Holding): string {
  if (Number.isFinite(holding.amount)) {
    if (holding.status === 'frozen') {
      if (holding.region === '华东') {
        if (holding.amount > 1_000_000) {
          return styles.toneCritical;
        } else {
          if (holding.amount > 500_000) {
            return styles.toneWarning;
          } else {
            return styles.toneMuted;
          }
        }
      } else {
        return styles.toneFrozen;
      }
    } else if (holding.status === 'closed') {
      return styles.toneClosed;
    }
    return styles.toneActive;
  }
  return styles.toneMuted;
}

export function HoldingsTable() {
  const [region, setRegion] = useState(REGIONS[0]);
  const { data, loading, error } = useHoldings(region);
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    setVisibleCount(data?.length ?? 0);
  }, [data]);

  if (loading) {
    return <div className={styles.placeholder}>加载中…</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  const sorted = [...(data ?? [])].sort((a, b) => b.amount - a.amount);

  return (
    <section className={styles.holdings}>
      <select
        className={styles.filter}
        value={region}
        onChange={(event) => setRegion(event.target.value)}
      >
        {REGIONS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <p className={styles.count}>共 {visibleCount} 条</p>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>地区</th>
            <th>金额</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((holding) => (
            <tr key={holding.id} className={getRowTone(holding)}>
              <td>{holding.region}</td>
              <td>{toAmountLabel(holding.amount)}</td>
              <td>{holding.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
