import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Typography,
    Table,
    Button,
    Space,
    Tag,
    Card,
    Select,
    Spin,
    Empty,
    Descriptions,
    Modal,
    Row,
    Col,
    Statistic,
} from 'antd';
import { ArrowLeftOutlined, EyeOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useFormQuery, useFormSubmissionsQuery, useFormAnalyticsQuery, FormSubmission } from '../services/formsService';

const { Title, Text } = Typography;

export default function FormSubmissions() {
    const { formId } = useParams<{ formId: string }>();
    const navigate = useNavigate();
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [statusFilter, setStatusFilter] = useState<string | undefined>();
    const [selectedSubmission, setSelectedSubmission] = useState<FormSubmission | null>(null);

    const { data: form, isLoading: formLoading } = useFormQuery(formId || '');
    const {
        data: submissions,
        isLoading: submissionsLoading,
        refetch,
    } = useFormSubmissionsQuery(formId || '', page, pageSize, statusFilter);
    const { data: analytics } = useFormAnalyticsQuery(formId || '');

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'processed':
                return 'green';
            case 'pending':
                return 'orange';
            case 'spam':
                return 'red';
            default:
                return 'default';
        }
    };

    const columns: ColumnsType<FormSubmission> = [
        {
            title: 'Submitted',
            dataIndex: 'submittedAt',
            key: 'submittedAt',
            width: 180,
            render: (date: string) => dayjs(date).format('MMM D, YYYY h:mm A'),
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: (status: string) => <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>,
        },
        {
            title: 'Summary',
            key: 'summary',
            render: (_, record) => {
                // Show first few field values
                const entries = Object.entries(record.field_values || {}).slice(0, 2);
                return (
                    <Space direction='vertical' size={0}>
                        {entries.map(([fieldId, value]) => {
                            const field = form?.fields?.find((f) => f.id === fieldId);
                            return (
                                <Text key={fieldId} type='secondary' style={{ fontSize: 12 }}>
                                    {field?.label || fieldId}: {String(value).substring(0, 50)}
                                    {String(value).length > 50 ? '...' : ''}
                                </Text>
                            );
                        })}
                    </Space>
                );
            },
        },
        {
            title: 'Actions',
            key: 'actions',
            width: 100,
            render: (_, record) => (
                <Button size='small' icon={<EyeOutlined />} onClick={() => setSelectedSubmission(record)}>
                    View
                </Button>
            ),
        },
    ];

    if (formLoading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
                <Spin size='large' />
            </div>
        );
    }

    if (!form) {
        return (
            <Empty description='Form not found'>
                <Button onClick={() => navigate('/forms')}>Back to Forms</Button>
            </Empty>
        );
    }

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space>
                    <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/forms')}>
                        Back
                    </Button>
                    <Title level={3} style={{ margin: 0 }}>
                        {form.name} - Submissions
                    </Title>
                </Space>

                <Space>
                    <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
                        Refresh
                    </Button>
                    <Button icon={<DownloadOutlined />}>Export CSV</Button>
                </Space>
            </div>

            {/* Stats */}
            {analytics && (
                <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col span={8}>
                        <Card>
                            <Statistic title='Total Submissions' value={analytics.total_submissions} />
                        </Card>
                    </Col>
                    <Col span={8}>
                        <Card>
                            <Statistic title='Today' value={analytics.submissions_today} />
                        </Card>
                    </Col>
                    <Col span={8}>
                        <Card>
                            <Statistic title='This Week' value={analytics.submissions_this_week} />
                        </Card>
                    </Col>
                </Row>
            )}

            {/* Submissions table */}
            <Card>
                <div style={{ marginBottom: 16 }}>
                    <Space>
                        <Text>Status:</Text>
                        <Select
                            style={{ width: 150 }}
                            placeholder='All statuses'
                            allowClear
                            value={statusFilter}
                            onChange={setStatusFilter}
                            options={[
                                { value: 'pending', label: 'Pending' },
                                { value: 'processed', label: 'Processed' },
                                { value: 'spam', label: 'Spam' },
                            ]}
                        />
                    </Space>
                </div>

                <Table
                    columns={columns}
                    dataSource={submissions?.items}
                    rowKey='id'
                    loading={submissionsLoading}
                    pagination={{
                        current: page,
                        pageSize,
                        total: submissions?.total,
                        showSizeChanger: true,
                        showTotal: (total) => `${total} submissions`,
                        onChange: (p, ps) => {
                            setPage(p);
                            setPageSize(ps);
                        },
                    }}
                />
            </Card>

            {/* Submission detail modal */}
            <Modal
                title='Submission Details'
                open={!!selectedSubmission}
                onCancel={() => setSelectedSubmission(null)}
                footer={[
                    <Button key='close' onClick={() => setSelectedSubmission(null)}>
                        Close
                    </Button>,
                ]}
                width={600}
            >
                {selectedSubmission && (
                    <div>
                        <Descriptions column={1} bordered size='small' style={{ marginBottom: 16 }}>
                            <Descriptions.Item label='Submitted'>
                                {dayjs(selectedSubmission.submitted_at).format('MMMM D, YYYY h:mm:ss A')}
                            </Descriptions.Item>
                            <Descriptions.Item label='Status'>
                                <Tag color={getStatusColor(selectedSubmission.status)}>
                                    {selectedSubmission.status.toUpperCase()}
                                </Tag>
                            </Descriptions.Item>
                            {selectedSubmission.contact_id && (
                                <Descriptions.Item label='Contact ID'>
                                    {selectedSubmission.contact_id}
                                </Descriptions.Item>
                            )}
                        </Descriptions>

                        <Title level={5}>Field Values</Title>
                        <Descriptions column={1} bordered size='small'>
                            {Object.entries(selectedSubmission.field_values || {}).map(([fieldId, value]) => {
                                const field = form?.fields?.find((f) => f.id === fieldId);
                                return (
                                    <Descriptions.Item key={fieldId} label={field?.label || fieldId}>
                                        {Array.isArray(value) ? value.join(', ') : String(value)}
                                    </Descriptions.Item>
                                );
                            })}
                        </Descriptions>
                    </div>
                )}
            </Modal>
        </div>
    );
}
