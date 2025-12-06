/**
 * AI Provider configuration tab for Settings page
 */

import { useEffect, useState } from 'react';
import {
    Form,
    Select,
    Button,
    Card,
    Space,
    Typography,
    Input,
    Alert,
    Spin,
    Progress,
    Descriptions,
    Radio,
    Tag,
    Result,
    Statistic,
    Row,
    Col,
} from 'antd';
import { App } from 'antd';
import {
    RobotOutlined,
    SaveOutlined,
    ApiOutlined,
    ThunderboltOutlined,
    LockOutlined,
    CloudOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '../../services/api';
import { useAuthStore } from '../../stores/authStore';
import {
    AIProvider,
    AIKeySource,
    getAIConfig,
    updateAIConfig,
    updateProviderConfig,
    testAIConnection,
    getAIUsage,
    PROVIDER_INFO,
    MODEL_OPTIONS,
    formatTokenCount,
    AITestResponse,
} from '../../services/aiService';

const { Title, Paragraph, Text } = Typography;
const { Password } = Input;

// Provider icons (using emoji for simplicity)
const PROVIDER_ICONS: Record<AIProvider, string> = {
    claude: '🔷',
    openai: '🟢',
    azure_openai: '☁️',
    ollama: '🦙',
};

export default function AITab() {
    const { message } = App.useApp();
    const [form] = Form.useForm();
    const queryClient = useQueryClient();
    const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

    // State for test results
    const [testResult, setTestResult] = useState<AITestResponse | null>(null);
    const [activeProvider, setActiveProvider] = useState<AIProvider>('claude');

    // Fetch AI config
    const { data: config, isLoading } = useQuery({
        queryKey: ['ai-config'],
        queryFn: getAIConfig,
        enabled: isAuthenticated,
    });

    // Fetch usage stats
    const { data: usage } = useQuery({
        queryKey: ['ai-usage'],
        queryFn: getAIUsage,
        enabled: isAuthenticated,
    });

    // Mutations
    const updateConfigMutation = useMutation({
        mutationFn: updateAIConfig,
        onSuccess: (data) => {
            queryClient.setQueryData(['ai-config'], data);
            message.success('AI configuration updated');
        },
        onError: (error) => {
            message.error(getErrorMessage(error));
        },
    });

    const updateProviderMutation = useMutation({
        mutationFn: ({ provider, update }: { provider: AIProvider; update: Record<string, string> }) =>
            updateProviderConfig(provider, update),
        onSuccess: (data) => {
            queryClient.setQueryData(['ai-config'], data);
            message.success('Provider configuration saved');
        },
        onError: (error) => {
            message.error(getErrorMessage(error));
        },
    });

    const testMutation = useMutation({
        mutationFn: testAIConnection,
        onSuccess: (result) => {
            setTestResult(result);
            if (result.success) {
                message.success(`Connection successful (${result.latency_ms}ms)`);
            } else {
                message.error(result.message);
            }
        },
        onError: (error) => {
            message.error(getErrorMessage(error));
        },
    });

    // Initialize form when config loads
    useEffect(() => {
        if (config) {
            setActiveProvider(config.ai_provider);
            form.setFieldsValue({
                ai_provider: config.ai_provider,
                ai_key_source: config.ai_key_source,
            });
        }
    }, [config, form]);

    const handleProviderChange = async (provider: AIProvider) => {
        setActiveProvider(provider);
        await updateConfigMutation.mutateAsync({ ai_provider: provider });
    };

    const handleKeySourceChange = async (source: AIKeySource) => {
        await updateConfigMutation.mutateAsync({ ai_key_source: source });
    };

    const handleSaveProviderConfig = async (provider: AIProvider, values: Record<string, string>) => {
        // Filter out empty values and undefined
        const update: Record<string, string> = {};
        Object.entries(values).forEach(([key, value]) => {
            if (value !== undefined && value !== '') {
                update[key] = value;
            }
        });

        if (Object.keys(update).length > 0) {
            await updateProviderMutation.mutateAsync({ provider, update });
        }
    };

    const handleTestConnection = async () => {
        setTestResult(null);
        await testMutation.mutateAsync({ provider: activeProvider });
    };

    if (isLoading) {
        return (
            <div style={{ textAlign: 'center', padding: 48 }}>
                <Spin size='large' />
            </div>
        );
    }

    const currentProviderConfig = config?.providers[activeProvider];
    const isPlatformKey = config?.ai_key_source === 'platform';

    return (
        <div>
            <Title level={4}>
                <RobotOutlined style={{ marginRight: 8 }} />
                AI Provider Configuration
            </Title>
            <Paragraph type='secondary'>
                Configure the AI provider used for message analysis, contact engagement scoring, and other AI-powered
                features.
            </Paragraph>

            {/* Usage Stats */}
            {usage && (
                <Card style={{ marginBottom: 24 }}>
                    <Row gutter={24}>
                        <Col span={8}>
                            <Statistic
                                title='Tokens Used This Month'
                                value={formatTokenCount(usage.tokens_used_this_month)}
                                prefix={<ThunderboltOutlined />}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title='Monthly Limit'
                                value={usage.monthly_limit ? formatTokenCount(usage.monthly_limit) : 'Unlimited'}
                                prefix={<ApiOutlined />}
                            />
                        </Col>
                        <Col span={8}>
                            {usage.monthly_limit && usage.percentage_used !== null && (
                                <div>
                                    <Text type='secondary'>Usage</Text>
                                    <Progress
                                        percent={usage.percentage_used}
                                        status={usage.percentage_used > 90 ? 'exception' : 'active'}
                                        style={{ marginTop: 8 }}
                                    />
                                </div>
                            )}
                            {!usage.monthly_limit && (
                                <Tag color='green' style={{ marginTop: 24 }}>
                                    <LockOutlined /> Using Own API Key
                                </Tag>
                            )}
                        </Col>
                    </Row>
                </Card>
            )}

            {/* Key Source Selection */}
            <Card title='API Key Source' style={{ marginBottom: 24 }}>
                <Form.Item
                    label='How should AI API keys be managed?'
                    help={
                        isPlatformKey
                            ? 'Using shared platform keys. Usage is metered against your subscription.'
                            : 'Using your own API keys. No usage limits from Dewey.'
                    }
                >
                    <Radio.Group
                        value={config?.ai_key_source}
                        onChange={(e) => handleKeySourceChange(e.target.value)}
                        disabled={updateConfigMutation.isPending}
                    >
                        <Radio.Button value='platform'>
                            <CloudOutlined /> Platform Keys
                        </Radio.Button>
                        <Radio.Button value='tenant'>
                            <LockOutlined /> My Own Keys
                        </Radio.Button>
                    </Radio.Group>
                </Form.Item>

                {isPlatformKey && (
                    <Alert
                        message='Platform Keys'
                        description={`Your ${config?.subscription_tier} tier includes ${
                            config?.ai_monthly_token_limit
                                ? formatTokenCount(config.ai_monthly_token_limit) + ' tokens/month'
                                : 'unlimited tokens'
                        }. Upgrade your plan for higher limits.`}
                        type='info'
                        showIcon
                    />
                )}
            </Card>

            {/* Provider Selection */}
            <Card title='Active AI Provider' style={{ marginBottom: 24 }}>
                <Radio.Group
                    value={activeProvider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    disabled={updateConfigMutation.isPending}
                    buttonStyle='solid'
                    size='large'
                    style={{ width: '100%' }}
                >
                    <Space direction='vertical' style={{ width: '100%' }}>
                        {(Object.keys(PROVIDER_INFO) as AIProvider[]).map((provider) => (
                            <Radio.Button
                                key={provider}
                                value={provider}
                                style={{
                                    width: '100%',
                                    height: 'auto',
                                    padding: '12px 16px',
                                    textAlign: 'left',
                                }}
                            >
                                <Space>
                                    <span style={{ fontSize: 20 }}>{PROVIDER_ICONS[provider]}</span>
                                    <div>
                                        <div>
                                            <Text strong>{PROVIDER_INFO[provider].name}</Text>
                                            {config?.ai_provider === provider && (
                                                <Tag color='blue' style={{ marginLeft: 8 }}>
                                                    Active
                                                </Tag>
                                            )}
                                            {config?.providers[provider]?.api_key_set && (
                                                <Tag color='green' style={{ marginLeft: 4 }}>
                                                    Key Set
                                                </Tag>
                                            )}
                                        </div>
                                        <Text type='secondary' style={{ fontSize: 12 }}>
                                            {PROVIDER_INFO[provider].description}
                                        </Text>
                                    </div>
                                </Space>
                            </Radio.Button>
                        ))}
                    </Space>
                </Radio.Group>
            </Card>

            {/* Provider-specific Configuration */}
            {!isPlatformKey && (
                <Card
                    title={
                        <Space>
                            <span>{PROVIDER_ICONS[activeProvider]}</span>
                            <span>{PROVIDER_INFO[activeProvider].name} Configuration</span>
                        </Space>
                    }
                    style={{ marginBottom: 24 }}
                >
                    <ProviderConfigForm
                        provider={activeProvider}
                        config={currentProviderConfig}
                        onSave={(values) => handleSaveProviderConfig(activeProvider, values)}
                        saving={updateProviderMutation.isPending}
                    />
                </Card>
            )}

            {/* Test Connection */}
            <Card title='Test Connection' style={{ marginBottom: 24 }}>
                <Space direction='vertical' style={{ width: '100%' }}>
                    <Paragraph>
                        Test the connection to verify your {PROVIDER_INFO[activeProvider].name} configuration is
                        working correctly.
                    </Paragraph>

                    <Button
                        type='primary'
                        icon={<ThunderboltOutlined />}
                        onClick={handleTestConnection}
                        loading={testMutation.isPending}
                    >
                        Test Connection
                    </Button>

                    {testResult && (
                        <Result
                            status={testResult.success ? 'success' : 'error'}
                            title={testResult.success ? 'Connection Successful' : 'Connection Failed'}
                            subTitle={testResult.message}
                            extra={
                                testResult.success && (
                                    <Descriptions column={1} size='small'>
                                        <Descriptions.Item label='Provider'>{testResult.provider}</Descriptions.Item>
                                        <Descriptions.Item label='Model'>{testResult.model}</Descriptions.Item>
                                        <Descriptions.Item label='Latency'>{testResult.latency_ms}ms</Descriptions.Item>
                                    </Descriptions>
                                )
                            }
                        />
                    )}
                </Space>
            </Card>

            {/* Current Configuration Summary */}
            <Card title='Current Configuration'>
                <Descriptions column={1} size='small'>
                    <Descriptions.Item label='Active Provider'>
                        <Tag color='blue'>
                            {PROVIDER_ICONS[config?.ai_provider as AIProvider]} {PROVIDER_INFO[config?.ai_provider as AIProvider]?.name}
                        </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label='Key Source'>
                        <Tag color={isPlatformKey ? 'orange' : 'green'}>
                            {isPlatformKey ? 'Platform Key' : 'Tenant Key'}
                        </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label='Model'>
                        {currentProviderConfig?.model || 'Default'}
                    </Descriptions.Item>
                    {currentProviderConfig?.api_key_masked && (
                        <Descriptions.Item label='API Key'>
                            <Text code>{currentProviderConfig.api_key_masked}</Text>
                        </Descriptions.Item>
                    )}
                </Descriptions>
            </Card>
        </div>
    );
}

// Provider-specific configuration form
interface ProviderConfigFormProps {
    provider: AIProvider;
    config?: {
        model: string | null;
        api_key_set: boolean;
        api_key_masked: string | null;
        endpoint?: string | null;
        deployment?: string | null;
        api_version?: string | null;
        base_url?: string | null;
    };
    onSave: (values: Record<string, string>) => Promise<void>;
    saving: boolean;
}

function ProviderConfigForm({ provider, config, onSave, saving }: ProviderConfigFormProps) {
    const [form] = Form.useForm();

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            await onSave(values);
            // Clear the API key field after save (it's now encrypted)
            form.setFieldValue('api_key', '');
        } catch {
            // Validation error
        }
    };

    return (
        <Form form={form} layout='vertical' initialValues={{ model: config?.model }}>
            {/* Model Selection */}
            <Form.Item name='model' label='Model'>
                <Select
                    placeholder='Select model'
                    options={MODEL_OPTIONS[provider]}
                    style={{ width: 300 }}
                />
            </Form.Item>

            {/* API Key (for providers that need it) */}
            {PROVIDER_INFO[provider].requiresKey && (
                <Form.Item
                    name='api_key'
                    label='API Key'
                    help={
                        config?.api_key_set
                            ? `Current key: ${config.api_key_masked}. Leave blank to keep existing key.`
                            : 'Enter your API key. It will be encrypted before storage.'
                    }
                >
                    <Password
                        placeholder={config?.api_key_set ? 'Leave blank to keep existing' : 'Enter API key'}
                        style={{ width: 400 }}
                    />
                </Form.Item>
            )}

            {/* Azure OpenAI specific fields */}
            {provider === 'azure_openai' && (
                <>
                    <Form.Item
                        name='endpoint'
                        label='Azure Endpoint'
                        help='e.g., https://your-resource.openai.azure.com'
                        initialValue={config?.endpoint}
                    >
                        <Input placeholder='https://your-resource.openai.azure.com' style={{ width: 400 }} />
                    </Form.Item>
                    <Form.Item
                        name='deployment'
                        label='Deployment Name'
                        help='The name of your Azure OpenAI deployment'
                        initialValue={config?.deployment}
                    >
                        <Input placeholder='gpt-4-deployment' style={{ width: 300 }} />
                    </Form.Item>
                    <Form.Item
                        name='api_version'
                        label='API Version'
                        initialValue={config?.api_version || '2024-02-15-preview'}
                    >
                        <Input placeholder='2024-02-15-preview' style={{ width: 200 }} />
                    </Form.Item>
                </>
            )}

            {/* Ollama specific fields */}
            {provider === 'ollama' && (
                <Form.Item
                    name='base_url'
                    label='Ollama Base URL'
                    help='URL where your Ollama instance is running'
                    initialValue={config?.base_url || 'http://localhost:11434'}
                >
                    <Input placeholder='http://localhost:11434' style={{ width: 300 }} />
                </Form.Item>
            )}

            <Form.Item style={{ marginTop: 24, marginBottom: 0 }}>
                <Button type='primary' icon={<SaveOutlined />} onClick={handleSubmit} loading={saving}>
                    Save Configuration
                </Button>
            </Form.Item>
        </Form>
    );
}
