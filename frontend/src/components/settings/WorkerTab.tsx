/**
 * Worker/Job Queue configuration tab for Settings page
 */

import { useEffect } from 'react';
import { Form, Select, Button, Card, Space, Typography, InputNumber, Alert, Spin, Descriptions } from 'antd';
import { App } from 'antd';
import { ThunderboltOutlined, ClockCircleOutlined, ReloadOutlined, SaveOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, getErrorMessage } from '../../services/api';
import { useAuthStore } from '../../stores/authStore';

const { Title, Paragraph, Text } = Typography;

// Types
interface WorkerSettings {
    max_concurrent_jobs: number;
    job_timeout_seconds: number;
    max_retries: number;
}

// API functions
const getWorkerSettings = async (): Promise<WorkerSettings> => {
    const response = await api.get<WorkerSettings>('/tenants/settings/worker');
    return response.data;
};

const updateWorkerSettings = async (settings: Partial<WorkerSettings>): Promise<WorkerSettings> => {
    const response = await api.patch<WorkerSettings>('/tenants/settings/worker', settings);
    return response.data;
};

// Timeout options in seconds
const timeoutOptions = [
    { value: 900, label: '15 minutes' },
    { value: 1800, label: '30 minutes' },
    { value: 3600, label: '1 hour' },
    { value: 7200, label: '2 hours' },
    { value: 14400, label: '4 hours' },
];

export default function WorkerTab() {
    const { message } = App.useApp();
    const [form] = Form.useForm();
    const queryClient = useQueryClient();
    const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

    const {
        data: settings,
        isLoading,
        refetch,
    } = useQuery({
        queryKey: ['worker-settings'],
        queryFn: getWorkerSettings,
        enabled: isAuthenticated,
    });

    const saveMutation = useMutation({
        mutationFn: updateWorkerSettings,
        onSuccess: (data) => {
            queryClient.setQueryData(['worker-settings'], data);
            message.success('Worker settings saved');
        },
        onError: (error) => {
            message.error(getErrorMessage(error));
        },
    });

    // Populate form when settings load
    useEffect(() => {
        if (settings) {
            form.setFieldsValue(settings);
        }
    }, [settings, form]);

    const handleSave = async () => {
        try {
            const values = await form.validateFields();
            await saveMutation.mutateAsync(values);
        } catch {
            // Form validation error
        }
    };

    if (isLoading) {
        return (
            <div style={{ textAlign: 'center', padding: 48 }}>
                <Spin size='large' />
            </div>
        );
    }

    return (
        <div>
            <Title level={4}>
                <ThunderboltOutlined style={{ marginRight: 8 }} />
                Job Queue Settings
            </Title>
            <Paragraph type='secondary'>
                Configure how background jobs (like voter imports) are processed. These settings affect job execution
                and retry behavior.
            </Paragraph>

            <Alert
                message='Worker Restart Required'
                description="Changes to 'Max Concurrent Jobs' require a worker restart to take effect. Timeout and retry settings apply to new jobs immediately."
                type='info'
                showIcon
                style={{ marginBottom: 24 }}
            />

            <Card>
                <Form form={form} layout='vertical' initialValues={settings}>
                    <Form.Item
                        name='max_concurrent_jobs'
                        label='Max Concurrent Jobs'
                        help='Number of jobs that can run simultaneously. Higher values process the queue faster but use more resources.'
                        rules={[{ required: true, message: 'Required' }]}
                    >
                        <InputNumber min={1} max={10} style={{ width: 200 }} addonAfter='jobs' />
                    </Form.Item>

                    <Form.Item
                        name='job_timeout_seconds'
                        label='Job Timeout'
                        help='Maximum time a job can run before being marked as failed. Increase for large imports.'
                        rules={[{ required: true, message: 'Required' }]}
                    >
                        <Select style={{ width: 200 }}>
                            {timeoutOptions.map((opt) => (
                                <Select.Option key={opt.value} value={opt.value}>
                                    {opt.label}
                                </Select.Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name='max_retries'
                        label='Max Retries'
                        help='Number of times to retry a failed job before giving up. Set to 0 to disable retries.'
                        rules={[{ required: true, message: 'Required' }]}
                    >
                        <InputNumber min={0} max={10} style={{ width: 200 }} addonAfter='attempts' />
                    </Form.Item>

                    <Form.Item style={{ marginTop: 24, marginBottom: 0 }}>
                        <Space>
                            <Button
                                type='primary'
                                icon={<SaveOutlined />}
                                onClick={handleSave}
                                loading={saveMutation.isPending}
                            >
                                Save Settings
                            </Button>
                            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
                                Reset
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Card>

            <Card style={{ marginTop: 24 }}>
                <Title level={5}>
                    <ClockCircleOutlined style={{ marginRight: 8 }} />
                    Current Configuration
                </Title>
                <Descriptions column={1} size='small'>
                    <Descriptions.Item label='Concurrent Jobs'>
                        <Text strong>{settings?.max_concurrent_jobs || 1}</Text>
                        <Text type='secondary'>&nbsp;(requires worker restart)</Text>
                    </Descriptions.Item>
                    <Descriptions.Item label='Job Timeout'>
                        <Text strong>
                            {timeoutOptions.find((o) => o.value === settings?.job_timeout_seconds)?.label ||
                                `${(settings?.job_timeout_seconds || 3600) / 60} minutes`}
                        </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label='Max Retries'>
                        <Text strong>{settings?.max_retries || 3}</Text>
                        <Text type='secondary'>&nbsp;(attempts before marking as failed)</Text>
                    </Descriptions.Item>
                </Descriptions>
            </Card>
        </div>
    );
}
