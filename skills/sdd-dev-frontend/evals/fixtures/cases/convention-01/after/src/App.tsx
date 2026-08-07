import { PortfolioPanel } from '@/features/portfolio/PortfolioPanel';
import RiskBriefPanel from './features/risk-brief/riskbrief_panel';
import './styles/tokens.css';

export function App() {
  return (
    <main>
      <PortfolioPanel />
      <RiskBriefPanel tenantName="示例租户" />
    </main>
  );
}
