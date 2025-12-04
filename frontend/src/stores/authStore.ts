import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authService, UserResponse } from '../services/authService';

// User interface matching backend UserResponse
export interface User {
  id: string;
  email: string;
  name: string;
  isActive: boolean;
  tenantId: string;
  tenantName: string;
  tenantSlug: string;
  roles: string[];
  permissions: string[];
}

// Transform backend response to frontend User type
export function mapUserResponse(response: UserResponse): User {
  return {
    id: response.id,
    email: response.email,
    name: response.name,
    isActive: response.is_active,
    tenantId: response.tenant_id,
    tenantName: response.tenant_name,
    tenantSlug: response.tenant_slug,
    roles: response.roles,
    permissions: response.permissions,
  };
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isInitialized: boolean;

  // Actions
  setAuth: (user: User, accessToken: string, refreshToken: string) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
  initialize: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isInitialized: false,

      setAuth: (user, accessToken, refreshToken) =>
        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
        }),

      setTokens: (accessToken, refreshToken) =>
        set({
          accessToken,
          refreshToken,
        }),

      setUser: (user) =>
        set({
          user,
        }),

      logout: () =>
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        }),

      /**
       * Initialize auth state on app load.
       * If tokens exist, validate them by fetching current user.
       */
      initialize: async () => {
        const { accessToken, logout } = get();

        if (!accessToken) {
          set({ isInitialized: true });
          return;
        }

        try {
          // Validate token and get current user info
          const userResponse = await authService.getCurrentUser();
          const user = mapUserResponse(userResponse);
          set({
            user,
            isAuthenticated: true,
            isInitialized: true,
          });
        } catch {
          // Token invalid or expired, logout
          logout();
          set({ isInitialized: true });
        }
      },

      hasPermission: (permission) => {
        const { user } = get();
        if (!user) return false;
        return user.permissions.includes(permission);
      },

      hasAnyPermission: (permissions) => {
        const { user } = get();
        if (!user) return false;
        return permissions.some((p) => user.permissions.includes(p));
      },

      hasAllPermissions: (permissions) => {
        const { user } = get();
        if (!user) return false;
        return permissions.every((p) => user.permissions.includes(p));
      },
    }),
    {
      name: 'dewey-auth',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
