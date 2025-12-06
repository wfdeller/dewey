import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Typography,
    Table,
    Button,
    Space,
    Tag,
    Modal,
    Form,
    Input,
    Select,
    message,
    Dropdown,
    Card,
    Row,
    Col,
    Statistic,
    Tabs,
    Progress,
    Tooltip,
    DatePicker,
} from 'antd';
import {
    PlusOutlined,
    PlayCircleOutlined,
    PauseCircleOutlined,
    StopOutlined,
    DeleteOutlined,
    MoreOutlined,
    MailOutlined,
    EyeOutlined,
    SendOutlined,
    ClockCircleOutlined,
    CheckCircleOutlined,
    ExclamationCircleOutlined,
    ScheduleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
    Campaign,
    CampaignStatus,
    useCampaignsQuery,
    useCampaignStatsQuery,
    useCreateCampaignMutation,
    useDeleteCampaignMutation,
    useStartCampaignMutation,
    usePauseCampaignMutation,
    useResumeCampaignMutation,
    useCancelCampaignMutation,
    useScheduleCampaignMutation,
} from '../services/campaignService';
import { useEmailTemplatesQuery } from '../services/emailService';
import { getErrorMessage } from '../services/api';
import RecommendationsPanel from '../components/campaigns/RecommendationsPanel';

const { Title, Text } = Typography;

// Status color mapping
const statusColors: Record<CampaignStatus, string> = {
    draft: 'default',
    scheduled: 'processing',
    active: 'green',
    paused: 'orange',
    completed: 'blue',
    cancelled: 'red',
};

const statusLabels: Record<CampaignStatus, string> = {
    draft: 'Draft',
    scheduled: 'Scheduled',
    active: 'Active',
    paused: 'Paused',
    completed: 'Completed',
    cancelled: 'Cancelled',
};

export default function Campaigns() {
    const navigate = useNavigate();
    const [statusFilter, setStatusFilter] = useState<CampaignStatus | undefined>();
    const [search, setSearch] = useState('');
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [createModalVisible, setCreateModalVisible] = useState(false);
    const [scheduleModal, setScheduleModal] = useState<{ visible: boolean; campaign?: Campaign }>({ visible: false });
    const [form] = Form.useForm();
    const [scheduleForm] = Form.useForm();

    // Queries
    const { data, isLoading, refetch } = useCampaignsQuery(page, pageSize, statusFilter, search || undefined);
    const { data: statsData } = useCampaignStatsQuery();
    const { data: templatesData } = useEmailTemplatesQuery(true); // Only active templates

    // Mutations
    const createMutation = useCreateCampaignMutation();
    const deleteMutation = useDeleteCampaignMutation();
    const startMutation = useStartCampaignMutation();
    const pauseMutation = usePauseCampaignMutation();
    const resumeMutation = useResumeCampaignMutation();
    const cancelMutation = useCancelCampaignMutation();
    const scheduleMutation = useScheduleCampaignMutation();

    // Handlers
    const handleCreate = async () => {
        try {
            const values = await form.validateFields();
            const campaign = await createMutation.mutateAsync({
                name: values.name,
                description: values.description,
                template_id: values.template_id,
                campaign_type: values.campaign_type || 'standard',
            });
            message.success('Campaign created successfully');
            setCreateModalVisible(false);
            form.resetFields();
            navigate(`/campaigns/${campaign.id}`);
        } catch (error) {
            if (error && typeof error === 'object' && 'errorFields' in error) return;
            message.error(getErrorMessage(error));
        }
    };

    const handleDelete = async (campaignId: string) => {
        try {
            await deleteMutation.mutateAsync(campaignId);
            message.success('Campaign deleted');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleStart = async (campaignId: string) => {
        try {
            await startMutation.mutateAsync(campaignId);
            message.success('Campaign started');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handlePause = async (campaignId: string) => {
        try {
            await pauseMutation.mutateAsync(campaignId);
            message.success('Campaign paused');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleResume = async (campaignId: string) => {
        try {
            await resumeMutation.mutateAsync(campaignId);
            message.success('Campaign resumed');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleCancel = async (campaignId: string) => {
        try {
            await cancelMutation.mutateAsync(campaignId);
            message.success('Campaign cancelled');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleSchedule = async () => {
        try {
            const values = await scheduleForm.validateFields();
            if (scheduleModal.campaign) {
                await scheduleMutation.mutateAsync({
                    campaignId: scheduleModal.campaign.id,
                    scheduled_at: values.scheduled_at.toISOString(),
                });
                message.success('Campaign scheduled');
                setScheduleModal({ visible: false });
                scheduleForm.resetFields();
                refetch();
            }
        } catch (error) {
            if (error && typeof error === 'object' && 'errorFields' in error) return;
            message.error(getErrorMessage(error));
        }
    };

    // Table columns
    const columns: ColumnsType<Campaign> = [
        {
            title: 'Name',
            dataIndex: 'name',
            key: 'name',
            render: (name: string, record) => (
                <Space direction='vertical' size={0}>
                    <Text strong style={{ cursor: 'pointer' }} onClick={() => navigate(`/campaigns/${record.id}`)}>
                        {name}
                    </Text>
                    {record.description && (
                        <Text type='secondary' style={{ fontSize: 12 }}>
                            {record.description}
                        </Text>
                    )}
                </Space>
            ),
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            width: 120,
            render: (status: CampaignStatus) => (
                <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
            ),
        },
        {
            title: 'Progress',
            key: 'progress',
            width: 180,
            render: (_, record) => {
                if (record.total_recipients === 0) {
                    return <Text type='secondary'>No recipients</Text>;
                }
                const percent = Math.round((record.total_sent / record.total_recipients) * 100);
                return (
                    <Tooltip title={`${record.total_sent.toLocaleString()} / ${record.total_recipients.toLocaleString()} sent`}>
                        <Progress percent={percent} size='small' status={record.status === 'active' ? 'active' : undefined} />
                    </Tooltip>
                );
            },
        },
        {
            title: 'Opens',
            key: 'opens',
            width: 100,
            render: (_, record) => {
                if (record.total_sent === 0) return '-';
                const rate = ((record.unique_opens / record.total_sent) * 100).toFixed(1);
                return (
                    <Tooltip title={`${record.unique_opens.toLocaleString()} unique opens`}>
                        <Text>{rate}%</Text>
                    </Tooltip>
                );
            },
        },
        {
            title: 'Clicks',
            key: 'clicks',
            width: 100,
            render: (_, record) => {
                if (record.total_sent === 0) return '-';
                const rate = ((record.unique_clicks / record.total_sent) * 100).toFixed(1);
                return (
                    <Tooltip title={`${record.unique_clicks.toLocaleString()} unique clicks`}>
                        <Text>{rate}%</Text>
                    </Tooltip>
                );
            },
        },
        {
            title: 'Created',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 120,
            render: (date: string) => dayjs(date).format('MMM D, YYYY'),
        },
        {
            title: 'Actions',
            key: 'actions',
            width: 150,
            render: (_, record) => {
                const menuItems = [];

                // View/Edit
                menuItems.push({
                    key: 'view',
                    icon: <EyeOutlined />,
                    label: record.status === 'draft' ? 'Edit' : 'View',
                    onClick: () => navigate(`/campaigns/${record.id}`),
                });

                // Status-specific actions
                if (record.status === 'draft') {
                    menuItems.push({
                        key: 'schedule',
                        icon: <ScheduleOutlined />,
                        label: 'Schedule',
                        onClick: () => {
                            setScheduleModal({ visible: true, campaign: record });
                        },
                    });
                    menuItems.push({
                        key: 'start',
                        icon: <PlayCircleOutlined />,
                        label: 'Start Now',
                        onClick: () => {
                            Modal.confirm({
                                title: 'Start Campaign',
                                content: 'Are you sure you want to start sending this campaign immediately?',
                                onOk: () => handleStart(record.id),
                            });
                        },
                    });
                }

                if (record.status === 'scheduled') {
                    menuItems.push({
                        key: 'start',
                        icon: <PlayCircleOutlined />,
                        label: 'Start Now',
                        onClick: () => handleStart(record.id),
                    });
                }

                if (record.status === 'active') {
                    menuItems.push({
                        key: 'pause',
                        icon: <PauseCircleOutlined />,
                        label: 'Pause',
                        onClick: () => handlePause(record.id),
                    });
                }

                if (record.status === 'paused') {
                    menuItems.push({
                        key: 'resume',
                        icon: <PlayCircleOutlined />,
                        label: 'Resume',
                        onClick: () => handleResume(record.id),
                    });
                }

                // Cancel (for active/scheduled/paused)
                if (['active', 'scheduled', 'paused'].includes(record.status)) {
                    menuItems.push({ type: 'divider' as const });
                    menuItems.push({
                        key: 'cancel',
                        icon: <StopOutlined />,
                        label: 'Cancel',
                        danger: true,
                        onClick: () => {
                            Modal.confirm({
                                title: 'Cancel Campaign',
                                content: 'Are you sure you want to cancel this campaign? This cannot be undone.',
                                okText: 'Cancel Campaign',
                                okType: 'danger',
                                onOk: () => handleCancel(record.id),
                            });
                        },
                    });
                }

                // Delete (only drafts)
                if (record.status === 'draft') {
                    menuItems.push({ type: 'divider' as const });
                    menuItems.push({
                        key: 'delete',
                        icon: <DeleteOutlined />,
                        label: 'Delete',
                        danger: true,
                        onClick: () => {
                            Modal.confirm({
                                title: 'Delete Campaign',
                                content: `Are you sure you want to delete "${record.name}"?`,
                                okText: 'Delete',
                                okType: 'danger',
                                onOk: () => handleDelete(record.id),
                            });
                        },
                    });
                }

                return (
                    <Dropdown menu={{ items: menuItems }} trigger={['click']}>
                        <Button icon={<MoreOutlined />} />
                    </Dropdown>
                );
            },
        },
    ];

    // Stats
    const stats = {
        total: statsData?.total_campaigns || 0,
        draft: statsData?.by_status?.draft || 0,
        active: statsData?.by_status?.active || 0,
        completed: statsData?.by_status?.completed || 0,
        totalSent: statsData?.total_sent || 0,
        totalOpened: statsData?.total_opened || 0,
    };

    // Tab items for status filter
    const tabItems = [
        { key: 'all', label: 'All Campaigns' },
        { key: 'draft', label: `Drafts (${stats.draft})` },
        { key: 'scheduled', label: 'Scheduled' },
        { key: 'active', label: 'Active' },
        { key: 'completed', label: 'Completed' },
        { key: 'cancelled', label: 'Cancelled' },
    ];

    return (
        <div>
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={2} style={{ margin: 0 }}>
                    Campaigns
                </Title>
                <Button type='primary' icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
                    Create Campaign
                </Button>
            </div>

            {/* Recommendations Panel */}
            <div style={{ marginBottom: 24 }}>
                <RecommendationsPanel maxItems={3} />
            </div>

            {/* Stats Cards */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={6}>
                    <Card>
                        <Statistic
                            title='Total Campaigns'
                            value={stats.total}
                            prefix={<MailOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card>
                        <Statistic
                            title='Active'
                            value={stats.active}
                            valueStyle={{ color: '#52c41a' }}
                            prefix={<PlayCircleOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card>
                        <Statistic
                            title='Total Sent'
                            value={stats.totalSent}
                            prefix={<SendOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card>
                        <Statistic
                            title='Total Opens'
                            value={stats.totalOpened}
                            prefix={<EyeOutlined />}
                        />
                    </Card>
                </Col>
            </Row>

            <Card>
                {/* Status Tabs */}
                <Tabs
                    activeKey={statusFilter || 'all'}
                    onChange={(key) => {
                        setStatusFilter(key === 'all' ? undefined : (key as CampaignStatus));
                        setPage(1);
                    }}
                    items={tabItems}
                    style={{ marginBottom: 16 }}
                />

                {/* Search */}
                <div style={{ marginBottom: 16 }}>
                    <Input.Search
                        placeholder='Search campaigns...'
                        allowClear
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onSearch={() => {
                            setPage(1);
                            refetch();
                        }}
                        style={{ width: 300 }}
                    />
                </div>

                {/* Table */}
                <Table
                    columns={columns}
                    dataSource={data?.items}
                    rowKey='id'
                    loading={isLoading}
                    pagination={{
                        current: page,
                        pageSize,
                        total: data?.total,
                        showSizeChanger: true,
                        showTotal: (total) => `${total} campaigns`,
                        onChange: (p, ps) => {
                            setPage(p);
                            setPageSize(ps);
                        },
                    }}
                />
            </Card>

            {/* Create Campaign Modal */}
            <Modal
                title='Create Campaign'
                open={createModalVisible}
                onOk={handleCreate}
                onCancel={() => {
                    setCreateModalVisible(false);
                    form.resetFields();
                }}
                confirmLoading={createMutation.isPending}
            >
                <Form form={form} layout='vertical'>
                    <Form.Item
                        name='name'
                        label='Campaign Name'
                        rules={[{ required: true, message: 'Please enter a campaign name' }]}
                    >
                        <Input placeholder='e.g., March Newsletter, Product Launch' />
                    </Form.Item>

                    <Form.Item name='description' label='Description'>
                        <Input.TextArea rows={2} placeholder='Brief description of this campaign' />
                    </Form.Item>

                    <Form.Item
                        name='template_id'
                        label='Email Template'
                        rules={[{ required: true, message: 'Please select a template' }]}
                    >
                        <Select
                            placeholder='Select an email template'
                            options={templatesData?.items.map((t) => ({
                                value: t.id,
                                label: t.name,
                            }))}
                        />
                    </Form.Item>

                    <Form.Item name='campaign_type' label='Campaign Type' initialValue='standard'>
                        <Select
                            options={[
                                { value: 'standard', label: 'Standard' },
                                { value: 'ab_test', label: 'A/B Test' },
                            ]}
                        />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Schedule Campaign Modal */}
            <Modal
                title='Schedule Campaign'
                open={scheduleModal.visible}
                onOk={handleSchedule}
                onCancel={() => {
                    setScheduleModal({ visible: false });
                    scheduleForm.resetFields();
                }}
                confirmLoading={scheduleMutation.isPending}
            >
                <Form form={scheduleForm} layout='vertical'>
                    <Form.Item
                        name='scheduled_at'
                        label='Send Date & Time'
                        rules={[{ required: true, message: 'Please select a date and time' }]}
                    >
                        <DatePicker
                            showTime
                            format='YYYY-MM-DD HH:mm'
                            disabledDate={(current) => current && current < dayjs().startOf('day')}
                            style={{ width: '100%' }}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
