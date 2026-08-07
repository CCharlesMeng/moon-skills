import styles from './StatCard.module.css';

export interface StatCardProps {
  label: string;
  value: string;
  tone?: 'default' | 'danger' | 'success';
  onSelect?: (label: string) => void;
}

export function StatCard({ label, value, tone = 'default', onSelect }: StatCardProps) {
  return (
    <button type="button" className={`${styles.card} ${styles[tone]}`} onClick={() => onSelect?.(label)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{value}</span>
    </button>
  );
}
