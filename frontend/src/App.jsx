import { HashRouter, Routes, Route } from 'react-router-dom';
import { StoreProvider } from './lib/mockStore';
import QueuePage from './pages/QueuePage';
import ReportPage from './pages/ReportPage';

export default function App() {
  return (
    <StoreProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<QueuePage />} />
          <Route path="/report/:jobId" element={<ReportPage />} />
        </Routes>
      </HashRouter>
    </StoreProvider>
  );
}
