import { useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { AboutPage } from './pages/AboutPage';
import { DashboardPage } from './pages/DashboardPage';
import { ModelPage } from './pages/ModelPage';
import { PredictPage } from './pages/PredictPage';

export default function App() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <AppShell
      mobileOpen={mobileOpen}
      onToggleMobile={() => setMobileOpen((open) => !open)}
      onCloseMobile={() => setMobileOpen(false)}
    >
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/predict" element={<PredictPage />} />
        <Route path="/model" element={<ModelPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
