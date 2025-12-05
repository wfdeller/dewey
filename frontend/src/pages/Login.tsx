import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Divider, message, Alert } from 'antd';
import { MailOutlined, LockOutlined, WindowsOutlined } from '@ant-design/icons';
import { useAuthStore, mapUserResponse } from '../stores/authStore';
import { authService } from '../services/authService';
import { getErrorMessage } from '../services/api';

interface LoginFormValues {
    email: string;
    password: string;
}

export default function Login() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [azureLoading, setAzureLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const setAuth = useAuthStore((state) => state.setAuth);

    const handleSubmit = async (values: LoginFormValues) => {
        setLoading(true);
        setError(null);

        try {
            // Login and get tokens
            const tokens = await authService.login({
                email: values.email,
                password: values.password,
            });

            // Get user info
            // Note: We need to set tokens first so the API interceptor can use them
            // Temporarily store tokens to make the /me request
            useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);

            const userResponse = await authService.getCurrentUser();
            const user = mapUserResponse(userResponse);

            // Set full auth state
            setAuth(user, tokens.access_token, tokens.refresh_token);

            message.success('Login successful!');
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

    const handleAzureLogin = async () => {
        setAzureLoading(true);
        setError(null);

        try {
            // Get Azure AD authorization URL
            const { auth_url } = await authService.getAzureAuthUrl();

            // Redirect to Azure AD
            // The backend will handle the callback and redirect back with tokens
            window.location.href = auth_url;
        } catch (err) {
            const errorMessage = getErrorMessage(err);
            if (errorMessage.includes('not configured')) {
                setError('Azure AD SSO is not configured for this instance.');
            } else {
                setError(errorMessage);
            }
            setAzureLoading(false);
        }
    };

    return (
        <div>
            {error && (
                <Alert
                    message={error}
                    type='error'
                    showIcon
                    closable
                    onClose={() => setError(null)}
                    style={{ marginBottom: 24 }}
                />
            )}

            <Form name='login' onFinish={handleSubmit} layout='vertical' size='large'>
                <Form.Item
                    name='email'
                    rules={[
                        { required: true, message: 'Please enter your email' },
                        { type: 'email', message: 'Please enter a valid email' },
                    ]}
                >
                    <Input prefix={<MailOutlined />} placeholder='Email address' autoComplete='email' />
                </Form.Item>

                <Form.Item name='password' rules={[{ required: true, message: 'Please enter your password' }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder='Password' autoComplete='current-password' />
                </Form.Item>

                <Form.Item>
                    <Button type='primary' htmlType='submit' block loading={loading}>
                        Sign In
                    </Button>
                </Form.Item>
            </Form>

            <Divider>or</Divider>

            <Button icon={<WindowsOutlined />} block size='large' onClick={handleAzureLogin} loading={azureLoading}>
                Sign in with Microsoft
            </Button>

            <div style={{ marginTop: 24, textAlign: 'center' }}>
                <span style={{ marginRight: 8 }}>Don't have an account?</span>
                <Link to='/register'>Sign up</Link>
            </div>
        </div>
    );
}
