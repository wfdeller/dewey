import { Outlet, Navigate } from 'react-router-dom';
import { Layout, theme } from 'antd';
import { useAuthStore } from '../stores';

const { Content } = Layout;

export default function AuthLayout() {
  const { token } = theme.useToken();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  // Redirect to dashboard if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <Layout style={{ minHeight: '100vh', background: token.colorBgLayout }}>
      <Content
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: 24,
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 400,
            background: token.colorBgContainer,
            padding: 32,
            borderRadius: token.borderRadiusLG,
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <h1 style={{ fontSize: 32, fontWeight: 600, margin: 0 }}>Dewey</h1>
            <p style={{ color: token.colorTextSecondary, margin: '8px 0 0' }}>
              AI-Powered Communication Processing
            </p>
          </div>
          <Outlet />
        </div>
      </Content>
    </Layout>
  );
}
