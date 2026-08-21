import { PortfolioPanel } from '@/features/portfolio/PortfolioPanel';
import { OrderExportPanel } from '@/features/order-export/OrderExportPanel';
import './styles/tokens.css';

export function App() {
  return (
    <main>
      <PortfolioPanel />
      <OrderExportPanel />
    </main>
  );
}
