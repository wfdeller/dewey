/**
 * API Keys management service
 */

import { api } from './api';

// Types
export interface Scope {
  key: string;
  name: string;
  description: string;
}

export interface ScopesResponse {
  scopes: Scope[];
}

export interface APIKey {
  id: string;
  tenant_id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit: number;
  expires_at: string | null;
  allowed_ips: string[] | null;
  last_used_at: string | null;
  usage_count: number;
  created_at: string;
}

export interface APIKeyCreateResponse extends APIKey {
  key: string; // Full key, only returned on create/rotate
}

export interface APIKeyCreateRequest {
  name: string;
  scopes: string[];
  rate_limit?: number;
  expires_at?: string;
  allowed_ips?: string[];
}

export interface APIKeyUpdateRequest {
  name?: string;
  scopes?: string[];
  rate_limit?: number;
  expires_at?: string | null;
  allowed_ips?: string[] | null;
}

// API Keys service
export const apiKeysService = {
  async listScopes(): Promise<ScopesResponse> {
    const response = await api.get<ScopesResponse>('/api-keys/scopes');
    return response.data;
  },

  async listApiKeys(): Promise<APIKey[]> {
    const response = await api.get<APIKey[]>('/api-keys');
    return response.data;
  },

  async getApiKey(keyId: string): Promise<APIKey> {
    const response = await api.get<APIKey>(`/api-keys/${keyId}`);
    return response.data;
  },

  async createApiKey(data: APIKeyCreateRequest): Promise<APIKeyCreateResponse> {
    const response = await api.post<APIKeyCreateResponse>('/api-keys', data);
    return response.data;
  },

  async updateApiKey(keyId: string, data: APIKeyUpdateRequest): Promise<APIKey> {
    const response = await api.patch<APIKey>(`/api-keys/${keyId}`, data);
    return response.data;
  },

  async deleteApiKey(keyId: string): Promise<void> {
    await api.delete(`/api-keys/${keyId}`);
  },

  async rotateApiKey(keyId: string): Promise<APIKeyCreateResponse> {
    const response = await api.post<APIKeyCreateResponse>(`/api-keys/${keyId}/rotate`);
    return response.data;
  },
};
