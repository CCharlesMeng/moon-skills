import { PortfolioPanel } from '@/features/portfolio/PortfolioPanel';
import { HoldingsTable } from '@/features/holdings/HoldingsTable';
import './styles/tokens.css';

export function App() {
  return (
    <main>
      <PortfolioPanel />
      <HoldingsTable />
    </main>
  );
}
