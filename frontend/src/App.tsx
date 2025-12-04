import { Routes, Route, Navigate } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { Spin } from 'antd';
import MainLayout from './layouts/MainLayout';
import AuthLayout from './layouts/AuthLayout';

// Lazy load pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Messages = lazy(() => import('./pages/Messages'));
const MessageDetail = lazy(() => import('./pages/MessageDetail'));
const Contacts = lazy(() => import('./pages/Contacts'));
const Categories = lazy(() => import('./pages/Categories'));
const Campaigns = lazy(() => import('./pages/Campaigns'));
const Workflows = lazy(() => import('./pages/Workflows'));
const Forms = lazy(() => import('./pages/Forms'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Settings = lazy(() => import('./pages/Settings'));
const Login = lazy(() => import('./pages/Login'));

// Loading component
const PageLoader = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100%',
    minHeight: '400px'
  }}>
    <Spin size="large" />
  </div>
);

function App() {
  // TODO: Implement actual auth check
  const isAuthenticated = true;

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Auth routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<Login />} />
        </Route>

        {/* Protected routes */}
        <Route
          element={
            isAuthenticated ? <MainLayout /> : <Navigate to="/login" replace />
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/messages" element={<Messages />} />
          <Route path="/messages/:id" element={<MessageDetail />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/campaigns" element={<Campaigns />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/forms" element={<Forms />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        {/* 404 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
