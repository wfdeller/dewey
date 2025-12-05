import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Spin, Result, Button } from 'antd';
import { useAuthStore, mapUserResponse } from '../stores/authStore';
import { authService } from '../services/authService';
import { getErrorMessage } from '../services/api';

export default function AzureCallback() {
    const navigate = useNavigate();
    const location = useLocation();
    const [error, setError] = useState<string | null>(null);
    const setAuth = useAuthStore((state) => state.setAuth);

    useEffect(() => {
        const handleCallback = async () => {
            // The backend redirects with tokens in the URL fragment (hash)
            // e.g., /auth/callback#access_token=xxx&refresh_token=yyy&token_type=bearer
            const hash = location.hash.substring(1); // Remove the '#'
            const hashParams = new URLSearchParams(hash);

            const accessToken = hashParams.get('access_token');
            const refreshToken = hashParams.get('refresh_token');

            // Check for error in query params (backend redirects errors to /auth/error?error=...)
            const queryParams = new URLSearchParams(location.search);
            const errorParam = queryParams.get('error');

            if (errorParam) {
                setError(errorParam);
                return;
            }

            // Validate tokens exist
            if (!accessToken || !refreshToken) {
                setError('Invalid callback: missing tokens');
                return;
            }

            try {
                // Set tokens to make the /me request
                useAuthStore.getState().setTokens(accessToken, refreshToken);

                // Get user info
                const userResponse = await authService.getCurrentUser();
                const user = mapUserResponse(userResponse);

                // Set full auth state
                setAuth(user, accessToken, refreshToken);

                // Navigate to dashboard
                navigate('/dashboard', { replace: true });
            } catch (err) {
                const errorMessage = getErrorMessage(err);
                setError(errorMessage);
                // Clear any partial token state
                useAuthStore.getState().logout();
            }
        };

        handleCallback();
    }, [location, navigate, setAuth]);

    if (error) {
        return (
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    minHeight: '100vh',
                    padding: 24,
                }}
            >
                <Result
                    status='error'
                    title='Authentication Failed'
                    subTitle={error}
                    extra={[
                        <Button type='primary' key='login' onClick={() => navigate('/login')}>
                            Back to Login
                        </Button>,
                    ]}
                />
            </div>
        );
    }

    return (
        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '100vh',
                gap: 16,
            }}
        >
            <Spin size='large' />
            <span>Completing sign in...</span>
        </div>
    );
}
