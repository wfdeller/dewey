/**
 * AI Configuration Service
 *
 * Handles API calls for AI provider configuration and testing.
 */

import { api } from './api';

// Types
export type AIProvider = 'claude' | 'openai' | 'azure_openai' | 'ollama';

export interface AIProviderConfig {
    provider: string;
    model: string | null;
    api_key_set: boolean;
    api_key_masked: string | null;
    // Azure OpenAI specific
    endpoint: string | null;
    deployment: string | null;
    api_version: string | null;
    // Ollama specific
    base_url: string | null;
}

export interface AIConfig {
    ai_provider: AIProvider;
    providers: Record<string, AIProviderConfig>;
}

export interface AIConfigUpdate {
    ai_provider?: AIProvider;
}

export interface AIProviderConfigUpdate {
    api_key?: string;
    model?: string;
    // Azure OpenAI specific
    endpoint?: string;
    deployment?: string;
    api_version?: string;
    // Ollama specific
    base_url?: string;
}

export interface AITestRequest {
    provider?: AIProvider;
}

export interface AITestResponse {
    success: boolean;
    provider: string;
    model: string | null;
    message: string;
    latency_ms: number | null;
}

// Provider display information
export const PROVIDER_INFO: Record<
    AIProvider,
    { name: string; description: string; requiresKey: boolean }
> = {
    claude: {
        name: 'Anthropic Claude',
        description: 'Advanced AI by Anthropic with strong analysis capabilities',
        requiresKey: true,
    },
    openai: {
        name: 'OpenAI GPT',
        description: 'GPT-4 and other models from OpenAI',
        requiresKey: true,
    },
    azure_openai: {
        name: 'Azure OpenAI',
        description: 'OpenAI models hosted on Microsoft Azure',
        requiresKey: true,
    },
    ollama: {
        name: 'Ollama (Self-hosted)',
        description: 'Run open-source models locally with Ollama',
        requiresKey: false,
    },
};

// Model options per provider
export const MODEL_OPTIONS: Record<AIProvider, { value: string; label: string }[]> = {
    claude: [
        { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus (Most Capable)' },
        { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet (Balanced)' },
        { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku (Fast)' },
        { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (Latest)' },
    ],
    openai: [
        { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
        { value: 'gpt-4', label: 'GPT-4' },
        { value: 'gpt-4o', label: 'GPT-4o' },
        { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
        { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
    ],
    azure_openai: [
        { value: 'gpt-4', label: 'GPT-4' },
        { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
        { value: 'gpt-35-turbo', label: 'GPT-3.5 Turbo' },
    ],
    ollama: [
        { value: 'llama2', label: 'Llama 2' },
        { value: 'llama3', label: 'Llama 3' },
        { value: 'mistral', label: 'Mistral' },
        { value: 'mixtral', label: 'Mixtral 8x7B' },
        { value: 'codellama', label: 'Code Llama' },
    ],
};

// API Functions

/**
 * Get AI configuration for the current tenant.
 */
export const getAIConfig = async (): Promise<AIConfig> => {
    const response = await api.get<AIConfig>('/tenants/settings/ai');
    return response.data;
};

/**
 * Update AI configuration (active provider).
 */
export const updateAIConfig = async (update: AIConfigUpdate): Promise<AIConfig> => {
    const response = await api.patch<AIConfig>('/tenants/settings/ai', update);
    return response.data;
};

/**
 * Update configuration for a specific provider.
 */
export const updateProviderConfig = async (
    provider: AIProvider,
    update: AIProviderConfigUpdate
): Promise<AIConfig> => {
    const response = await api.patch<AIConfig>(`/tenants/settings/ai/providers/${provider}`, update);
    return response.data;
};

/**
 * Test AI provider connection.
 */
export const testAIConnection = async (request: AITestRequest = {}): Promise<AITestResponse> => {
    const response = await api.post<AITestResponse>('/tenants/settings/ai/test', request);
    return response.data;
};
