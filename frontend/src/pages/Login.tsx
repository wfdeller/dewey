import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Divider, message } from 'antd';
import { MailOutlined, LockOutlined, WindowsOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores';

interface LoginFormValues {
  email: string;
  password: string;
}

export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((state) => state.setAuth);

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true);
    try {
      // TODO: Implement actual login API call
      // For now, mock a successful login
      await new Promise((resolve) => setTimeout(resolve, 1000));

      setAuth(
        {
          id: '1',
          email: values.email,
          name: 'Demo User',
          tenantId: '1',
          roles: ['admin'],
          permissions: ['messages:read', 'messages:write', 'contacts:read'],
        },
        'mock-access-token',
        'mock-refresh-token'
      );

      message.success('Login successful!');
      navigate('/dashboard');
    } catch (error) {
      message.error('Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleAzureLogin = () => {
    // TODO: Implement Azure AD SSO
    message.info('Azure AD SSO will be implemented');
  };

  return (
    <div>
      <Form
        name="login"
        onFinish={handleSubmit}
        layout="vertical"
        size="large"
      >
        <Form.Item
          name="email"
          rules={[
            { required: true, message: 'Please enter your email' },
            { type: 'email', message: 'Please enter a valid email' },
          ]}
        >
          <Input
            prefix={<MailOutlined />}
            placeholder="Email address"
            autoComplete="email"
          />
        </Form.Item>

        <Form.Item
          name="password"
          rules={[{ required: true, message: 'Please enter your password' }]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Password"
            autoComplete="current-password"
          />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            Sign In
          </Button>
        </Form.Item>
      </Form>

      <Divider>or</Divider>

      <Button
        icon={<WindowsOutlined />}
        block
        size="large"
        onClick={handleAzureLogin}
      >
        Sign in with Microsoft
      </Button>

      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <a href="/forgot-password">Forgot password?</a>
      </div>
    </div>
  );
}
