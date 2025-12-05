/**
 * Users and Roles API service
 */

import { api } from './api';

// Types
export interface UserListItem {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  azure_ad_oid: string | null;
  roles: string[];
  created_at: string;
  last_login_at: string | null;
}

export interface UserListResponse {
  users: UserListItem[];
  total: number;
}

export interface UserRoleResponse {
  role_id: string;
  role_name: string;
  assigned_at: string;
  assigned_by: string | null;
}

export interface UserDetailResponse {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  azure_ad_oid: string | null;
  tenant_id: string;
  roles: UserRoleResponse[];
  permissions: string[];
  created_at: string;
  updated_at: string;
}

export interface UserUpdateRequest {
  name?: string;
  is_active?: boolean;
}

export interface UserRoleAssignment {
  role_id: string;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: string[];
  azure_ad_group_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface RoleListResponse {
  roles: Role[];
  total: number;
}

export interface RoleCreateRequest {
  name: string;
  description?: string;
  permissions: string[];
  azure_ad_group_id?: string;
}

export interface RoleUpdateRequest {
  name?: string;
  description?: string;
  permissions?: string[];
  azure_ad_group_id?: string | null;
}

export interface PermissionInfo {
  key: string;
  name: string;
  description: string;
  category: string;
}

export interface PermissionListResponse {
  permissions: PermissionInfo[];
}

export interface UserListParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
}

// User API
export const usersService = {
  async listUsers(params: UserListParams = {}): Promise<UserListResponse> {
    const response = await api.get<UserListResponse>('/users', { params });
    return response.data;
  },

  async getUser(userId: string): Promise<UserDetailResponse> {
    const response = await api.get<UserDetailResponse>(`/users/${userId}`);
    return response.data;
  },

  async updateUser(userId: string, data: UserUpdateRequest): Promise<UserDetailResponse> {
    const response = await api.patch<UserDetailResponse>(`/users/${userId}`, data);
    return response.data;
  },

  async getUserRoles(userId: string): Promise<UserRoleResponse[]> {
    const response = await api.get<UserRoleResponse[]>(`/users/${userId}/roles`);
    return response.data;
  },

  async assignRole(userId: string, roleId: string): Promise<UserRoleResponse> {
    const response = await api.post<UserRoleResponse>(`/users/${userId}/roles`, {
      role_id: roleId,
    });
    return response.data;
  },

  async removeRole(userId: string, roleId: string): Promise<void> {
    await api.delete(`/users/${userId}/roles/${roleId}`);
  },

  async setUserRoles(userId: string, roleIds: string[]): Promise<UserRoleResponse[]> {
    const response = await api.put<UserRoleResponse[]>(`/users/${userId}/roles`, roleIds);
    return response.data;
  },
};

// Roles API
export const rolesService = {
  async listRoles(): Promise<RoleListResponse> {
    const response = await api.get<RoleListResponse>('/roles');
    return response.data;
  },

  async getRole(roleId: string): Promise<Role> {
    const response = await api.get<Role>(`/roles/${roleId}`);
    return response.data;
  },

  async createRole(data: RoleCreateRequest): Promise<Role> {
    const response = await api.post<Role>('/roles', data);
    return response.data;
  },

  async updateRole(roleId: string, data: RoleUpdateRequest): Promise<Role> {
    const response = await api.patch<Role>(`/roles/${roleId}`, data);
    return response.data;
  },

  async deleteRole(roleId: string): Promise<void> {
    await api.delete(`/roles/${roleId}`);
  },

  async resetRole(roleId: string): Promise<Role> {
    const response = await api.post<Role>(`/roles/${roleId}/reset`);
    return response.data;
  },

  async listPermissions(): Promise<PermissionListResponse> {
    const response = await api.get<PermissionListResponse>('/roles/permissions');
    return response.data;
  },
};
