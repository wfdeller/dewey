import { Routes, Route, Navigate } from 'react-router-dom';
import { Suspense, lazy, useEffect } from 'react';
import { Spin } from 'antd';
import MainLayout from './layouts/MainLayout';
import AuthLayout from './layouts/AuthLayout';
import { useAuthStore } from './stores/authStore';

// Lazy load pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Messages = lazy(() => import('./pages/Messages'));
const MessageDetail = lazy(() => import('./pages/MessageDetail'));
const Contacts = lazy(() => import('./pages/Contacts'));
const Categories = lazy(() => import('./pages/Categories'));
const Campaigns = lazy(() => import('./pages/Campaigns'));
const Workflows = lazy(() => import('./pages/Workflows'));
const Forms = lazy(() => import('./pages/Forms'));
const FormBuilder = lazy(() => import('./pages/FormBuilder'));
const FormSubmissions = lazy(() => import('./pages/FormSubmissions'));
const FormEmbed = lazy(() => import('./pages/FormEmbed'));
const FormLinks = lazy(() => import('./pages/FormLinks'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Settings = lazy(() => import('./pages/Settings'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const AzureCallback = lazy(() => import('./pages/AzureCallback'));

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

// Full page loader for auth initialization
const FullPageLoader = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
  }}>
    <Spin size="large" />
  </div>
);

function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isInitialized = useAuthStore((state) => state.isInitialized);
  const initialize = useAuthStore((state) => state.initialize);

  // Initialize auth state on app load
  useEffect(() => {
    initialize();
  }, [initialize]);

  // Show loading while auth state is being initialized
  if (!isInitialized) {
    return <FullPageLoader />;
  }

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Auth routes (public) */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>

        {/* Azure AD callback (public, no layout) */}
        <Route path="/auth/callback" element={<AzureCallback />} />

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
          <Route path="/forms/:formId/builder" element={<FormBuilder />} />
          <Route path="/forms/:formId/submissions" element={<FormSubmissions />} />
          <Route path="/forms/:formId/embed" element={<FormEmbed />} />
          <Route path="/forms/:formId/links" element={<FormLinks />} />
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
