import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Spin, Result, Button } from 'antd';
import { useAuthStore, mapUserResponse } from '../stores/authStore';
import { authService } from '../services/authService';
import { getErrorMessage } from '../services/api';

// Key for storing Azure AD state in sessionStorage
const AZURE_STATE_KEY = 'dewey-azure-state';

export default function AzureCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const setAuth = useAuthStore((state) => state.setAuth);

  useEffect(() => {
    const handleCallback = async () => {
      // Get code and state from URL
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const errorParam = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // Check for error from Azure AD
      if (errorParam) {
        setError(errorDescription || errorParam);
        return;
      }

      // Validate code and state exist
      if (!code || !state) {
        setError('Invalid callback: missing authorization code or state');
        return;
      }

      // Verify state matches what we stored (CSRF protection)
      const storedState = sessionStorage.getItem(AZURE_STATE_KEY);
      if (state !== storedState) {
        setError('Invalid callback: state mismatch (possible CSRF attack)');
        return;
      }

      // Clear stored state
      sessionStorage.removeItem(AZURE_STATE_KEY);

      try {
        // Exchange code for tokens
        const tokens = await authService.azureCallback({ code, state });

        // Set tokens to make the /me request
        useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);

        // Get user info
        const userResponse = await authService.getCurrentUser();
        const user = mapUserResponse(userResponse);

        // Set full auth state
        setAuth(user, tokens.access_token, tokens.refresh_token);

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
  }, [searchParams, navigate, setAuth]);

  if (error) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        padding: 24,
      }}>
        <Result
          status="error"
          title="Authentication Failed"
          subTitle={error}
          extra={[
            <Button type="primary" key="login" onClick={() => navigate('/login')}>
              Back to Login
            </Button>,
          ]}
        />
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      gap: 16,
    }}>
      <Spin size="large" />
      <span>Completing sign in...</span>
    </div>
  );
}
