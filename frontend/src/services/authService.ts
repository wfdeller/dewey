import { api } from './api';

// Request types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  tenant_name: string;
  tenant_slug: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

// Response types (matching backend schemas)
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  roles: string[];
  permissions: string[];
}

export interface AzureAuthUrlResponse {
  auth_url: string;
  state: string;
}

export interface AzureCallbackRequest {
  code: string;
  state: string;
}

// Auth service functions
export const authService = {
  /**
   * Login with email and password
   */
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/login', data);
    return response.data;
  },

  /**
   * Register a new user and tenant
   */
  async register(data: RegisterRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/register', data);
    return response.data;
  },

  /**
   * Refresh access token using refresh token
   */
  async refresh(refreshToken: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  /**
   * Get current authenticated user info
   */
  async getCurrentUser(): Promise<UserResponse> {
    const response = await api.get<UserResponse>('/auth/me');
    return response.data;
  },

  /**
   * Get Azure AD authorization URL for SSO
   */
  async getAzureAuthUrl(): Promise<AzureAuthUrlResponse> {
    const response = await api.get<AzureAuthUrlResponse>('/auth/azure/login');
    return response.data;
  },

  /**
   * Exchange Azure AD authorization code for tokens
   */
  async azureCallback(data: AzureCallbackRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/azure/callback', data);
    return response.data;
  },

  /**
   * Link Azure AD account to existing user
   */
  async linkAzureAccount(code: string): Promise<UserResponse> {
    const response = await api.post<UserResponse>('/auth/azure/link', { code });
    return response.data;
  },
};

export default authService;
