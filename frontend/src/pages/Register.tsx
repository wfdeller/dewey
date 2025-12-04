import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, message, Alert, Typography } from 'antd';
import {
  MailOutlined,
  LockOutlined,
  UserOutlined,
  BankOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useAuthStore, mapUserResponse } from '../stores/authStore';
import { authService } from '../services/authService';
import { getErrorMessage } from '../services/api';

const { Text } = Typography;

interface RegisterFormValues {
  email: string;
  password: string;
  confirmPassword: string;
  name: string;
  tenant_name: string;
  tenant_slug: string;
}

export default function Register() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setAuth = useAuthStore((state) => state.setAuth);

  // Auto-generate slug from tenant name
  const handleTenantNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value;
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    form.setFieldsValue({ tenant_slug: slug });
  };

  const handleSubmit = async (values: RegisterFormValues) => {
    setLoading(true);
    setError(null);

    try {
      // Register and get tokens
      const tokens = await authService.register({
        email: values.email,
        password: values.password,
        name: values.name,
        tenant_name: values.tenant_name,
        tenant_slug: values.tenant_slug,
      });

      // Set tokens to make the /me request
      useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);

      // Get user info
      const userResponse = await authService.getCurrentUser();
      const user = mapUserResponse(userResponse);

      // Set full auth state
      setAuth(user, tokens.access_token, tokens.refresh_token);

      message.success('Registration successful! Welcome to Dewey.');
      navigate('/dashboard');
    } catch (err) {
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      // Clear any partial token state
      useAuthStore.getState().logout();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 24, textAlign: 'center' }}>
        <Text type="secondary">
          Create your organization account
        </Text>
      </div>

      {error && (
        <Alert
          message={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 24 }}
        />
      )}

      <Form
        form={form}
        name="register"
        onFinish={handleSubmit}
        layout="vertical"
        size="large"
      >
        <Form.Item
          name="name"
          rules={[{ required: true, message: 'Please enter your name' }]}
        >
          <Input
            prefix={<UserOutlined />}
            placeholder="Your name"
            autoComplete="name"
          />
        </Form.Item>

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
          rules={[
            { required: true, message: 'Please enter a password' },
            { min: 8, message: 'Password must be at least 8 characters' },
          ]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Password"
            autoComplete="new-password"
          />
        </Form.Item>

        <Form.Item
          name="confirmPassword"
          dependencies={['password']}
          rules={[
            { required: true, message: 'Please confirm your password' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('password') === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error('Passwords do not match'));
              },
            }),
          ]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Confirm password"
            autoComplete="new-password"
          />
        </Form.Item>

        <Form.Item
          name="tenant_name"
          rules={[{ required: true, message: 'Please enter your organization name' }]}
        >
          <Input
            prefix={<BankOutlined />}
            placeholder="Organization name"
            onChange={handleTenantNameChange}
          />
        </Form.Item>

        <Form.Item
          name="tenant_slug"
          rules={[
            { required: true, message: 'Please enter a URL slug' },
            {
              pattern: /^[a-z0-9-]+$/,
              message: 'Slug can only contain lowercase letters, numbers, and hyphens',
            },
          ]}
          extra="This will be used in your organization's URL"
        >
          <Input
            prefix={<LinkOutlined />}
            placeholder="organization-slug"
            addonBefore="dewey.app/"
          />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            Create Account
          </Button>
        </Form.Item>
      </Form>

      <div style={{ textAlign: 'center' }}>
        <span style={{ marginRight: 8 }}>Already have an account?</span>
        <Link to="/login">Sign in</Link>
      </div>
    </div>
  );
}
