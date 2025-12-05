/**
 * API Key create/edit modal
 */

import { useEffect, useMemo } from 'react';
import {
    Modal,
    Form,
    Input,
    Checkbox,
    InputNumber,
    DatePicker,
    Space,
    Alert,
    message,
    Spin,
    Typography,
    Divider,
} from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { apiKeysService, APIKey, APIKeyCreateRequest, APIKeyUpdateRequest, Scope } from '../../services/apiKeysService';
import { getErrorMessage } from '../../services/api';

const { Text } = Typography;
const { TextArea } = Input;

interface ApiKeyModalProps {
    apiKey: APIKey | null;
    isCreating: boolean;
    open: boolean;
    onClose: (newKey?: string) => void;
}

export default function ApiKeyModal({ apiKey, isCreating, open, onClose }: ApiKeyModalProps) {
    const queryClient = useQueryClient();
    const [form] = Form.useForm();

    // Fetch available scopes
    const { data: scopesData, isLoading: scopesLoading } = useQuery({
        queryKey: ['api-key-scopes'],
        queryFn: () => apiKeysService.listScopes(),
        enabled: open,
    });

    // Group scopes by category (before the colon)
    const scopesByCategory = useMemo(() => {
        if (!scopesData?.scopes) return {};

        return scopesData.scopes.reduce((acc: Record<string, Scope[]>, scope: Scope) => {
            const category = scope.key.split(':')[0];
            const categoryName = category.charAt(0).toUpperCase() + category.slice(1);
            if (!acc[categoryName]) {
                acc[categoryName] = [];
            }
            acc[categoryName].push(scope);
            return acc;
        }, {});
    }, [scopesData]);

    // Create API key mutation
    const createMutation = useMutation({
        mutationFn: (data: APIKeyCreateRequest) => apiKeysService.createApiKey(data),
        onSuccess: (response) => {
            queryClient.invalidateQueries({ queryKey: ['api-keys'] });
            message.success('API key created successfully');
            onClose(response.key);
        },
        onError: (error) => {
            message.error(getErrorMessage(error));
        },
    });

    // Update API key mutation
    const updateMutation = useMutation({
        mutationFn: (data: APIKeyUpdateRequest) => apiKeysService.updateApiKey(apiKey!.id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['api-keys'] });
            message.success('API key updated successfully');
            onClose();
        },
        onError: (error) => {
            message.error(getErrorMessage(error));
        },
    });

    // Populate form when API key data loads
    useEffect(() => {
        if (open && apiKey && !isCreating) {
            form.setFieldsValue({
                name: apiKey.name,
                scopes: apiKey.scopes,
                rate_limit: apiKey.rate_limit,
                expires_at: apiKey.expires_at ? dayjs(apiKey.expires_at) : null,
                allowed_ips: apiKey.allowed_ips?.join('\n') || '',
            });
        } else if (open && isCreating) {
            form.resetFields();
            form.setFieldsValue({
                rate_limit: 60,
            });
        }
    }, [apiKey, isCreating, open, form]);

    // Reset form when modal closes
    useEffect(() => {
        if (!open) {
            form.resetFields();
        }
    }, [open, form]);

    const handleSave = async () => {
        try {
            const values = await form.validateFields();

            // Parse allowed IPs from textarea
            const allowedIps = values.allowed_ips
                ? values.allowed_ips
                      .split('\n')
                      .map((ip: string) => ip.trim())
                      .filter((ip: string) => ip)
                : null;

            if (isCreating) {
                const data: APIKeyCreateRequest = {
                    name: values.name,
                    scopes: values.scopes || [],
                    rate_limit: values.rate_limit,
                    expires_at: values.expires_at ? values.expires_at.toISOString() : undefined,
                    allowed_ips: allowedIps?.length ? allowedIps : undefined,
                };
                await createMutation.mutateAsync(data);
            } else {
                const data: APIKeyUpdateRequest = {
                    name: values.name,
                    scopes: values.scopes,
                    rate_limit: values.rate_limit,
                    expires_at: values.expires_at ? values.expires_at.toISOString() : null,
                    allowed_ips: allowedIps,
                };
                await updateMutation.mutateAsync(data);
            }
        } catch {
            // Form validation error - handled by antd
        }
    };

    const isSaving = createMutation.isPending || updateMutation.isPending;

    const renderScopesSelector = () => {
        if (scopesLoading) {
            return (
                <div style={{ textAlign: 'center', padding: 20 }}>
                    <Spin />
                </div>
            );
        }

        const categories = Object.keys(scopesByCategory).sort();

        return (
            <Form.Item name='scopes' rules={[{ required: true, message: 'At least one scope is required' }]}>
                <Checkbox.Group style={{ width: '100%' }}>
                    <Space direction='vertical' style={{ width: '100%' }}>
                        {categories.map((category) => (
                            <div key={category}>
                                <Text strong style={{ marginBottom: 8, display: 'block' }}>
                                    {category}
                                </Text>
                                <Space direction='vertical' style={{ marginLeft: 16, width: '100%' }}>
                                    {scopesByCategory[category].map((scope: Scope) => (
                                        <Checkbox key={scope.key} value={scope.key}>
                                            <Space direction='vertical' size={0}>
                                                <span>{scope.name}</span>
                                                <Text type='secondary' style={{ fontSize: 12 }}>
                                                    {scope.description}
                                                </Text>
                                            </Space>
                                        </Checkbox>
                                    ))}
                                </Space>
                                <Divider style={{ margin: '12px 0' }} />
                            </div>
                        ))}
                    </Space>
                </Checkbox.Group>
            </Form.Item>
        );
    };

    return (
        <Modal
            title={isCreating ? 'Create API Key' : `Edit API Key: ${apiKey?.name}`}
            open={open}
            onCancel={() => onClose()}
            onOk={handleSave}
            okText={isCreating ? 'Create' : 'Save Changes'}
            confirmLoading={isSaving}
            width={600}
        >
            <Form form={form} layout='vertical'>
                {isCreating && (
                    <Alert
                        message='Important'
                        description='The API key will only be shown once after creation. Make sure to copy and store it securely.'
                        type='info'
                        showIcon
                        style={{ marginBottom: 16 }}
                    />
                )}

                <Form.Item
                    name='name'
                    label='Name'
                    rules={[
                        { required: true, message: 'Name is required' },
                        { max: 100, message: 'Name must be 100 characters or less' },
                    ]}
                    extra="A descriptive name to identify this API key's purpose"
                >
                    <Input placeholder='e.g., Power BI Integration' />
                </Form.Item>

                <Form.Item
                    name='rate_limit'
                    label='Rate Limit (requests per minute)'
                    rules={[{ required: true, message: 'Rate limit is required' }]}
                >
                    <InputNumber min={1} max={10000} style={{ width: '100%' }} />
                </Form.Item>

                <Form.Item
                    name='expires_at'
                    label='Expiration Date (Optional)'
                    extra='Leave empty for a non-expiring key'
                >
                    <DatePicker
                        style={{ width: '100%' }}
                        showTime
                        format='YYYY-MM-DD HH:mm'
                        disabledDate={(current) => current && current < dayjs().startOf('day')}
                    />
                </Form.Item>

                <Form.Item
                    name='allowed_ips'
                    label='Allowed IP Addresses (Optional)'
                    extra='Enter one IP address per line. Leave empty to allow all IPs.'
                >
                    <TextArea
                        placeholder='192.168.1.1&#10;10.0.0.0/8'
                        rows={3}
                    />
                </Form.Item>

                <Form.Item label='Scopes' required>
                    {renderScopesSelector()}
                </Form.Item>
            </Form>
        </Modal>
    );
}
