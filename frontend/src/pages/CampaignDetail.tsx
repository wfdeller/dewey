import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Typography,
    Card,
    Row,
    Col,
    Statistic,
    Tag,
    Button,
    Space,
    Table,
    Tabs,
    Progress,
    Descriptions,
    Modal,
    Form,
    Input,
    Select,
    message,
    Spin,
    Alert,
    DatePicker,
    Tooltip,
    Divider,
} from 'antd';
import {
    ArrowLeftOutlined,
    PlayCircleOutlined,
    PauseCircleOutlined,
    StopOutlined,
    EditOutlined,
    SendOutlined,
    EyeOutlined,
    MailOutlined,
    UserOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    ExclamationCircleOutlined,
    ClockCircleOutlined,
    ScheduleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
    CampaignStatus,
    CampaignRecipient,
    RecipientStatus,
    useCampaignQuery,
    useCampaignRecipientsQuery,
    useCampaignAnalyticsQuery,
    useUpdateCampaignMutation,
    useStartCampaignMutation,
    usePauseCampaignMutation,
    useResumeCampaignMutation,
    useCancelCampaignMutation,
    useScheduleCampaignMutation,
    usePopulateRecipientsMutation,
    useTestSendMutation,
} from '../services/campaignService';
import { useEmailTemplatesQuery } from '../services/emailService';
import { getErrorMessage } from '../services/api';

const { Title, Text, Paragraph } = Typography;

// Status colors
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

const recipientStatusColors: Record<RecipientStatus, string> = {
    pending: 'default',
    queued: 'processing',
    sent: 'blue',
    delivered: 'cyan',
    opened: 'green',
    clicked: 'lime',
    bounced: 'red',
    failed: 'red',
    unsubscribed: 'orange',
};

export default function CampaignDetail() {
    const { campaignId } = useParams<{ campaignId: string }>();
    const navigate = useNavigate();
    const [recipientPage, setRecipientPage] = useState(1);
    const [recipientStatus, setRecipientStatus] = useState<RecipientStatus | undefined>();
    const [editModalVisible, setEditModalVisible] = useState(false);
    const [scheduleModalVisible, setScheduleModalVisible] = useState(false);
    const [testSendModalVisible, setTestSendModalVisible] = useState(false);
    const [form] = Form.useForm();
    const [scheduleForm] = Form.useForm();
    const [testSendForm] = Form.useForm();

    // Queries
    const { data: campaign, isLoading, refetch } = useCampaignQuery(campaignId || '');
    const { data: recipientsData, isLoading: recipientsLoading } = useCampaignRecipientsQuery(
        campaignId || '',
        recipientPage,
        50,
        recipientStatus
    );
    const { data: analytics } = useCampaignAnalyticsQuery(campaignId || '');
    const { data: templatesData } = useEmailTemplatesQuery(true);

    // Mutations
    const updateMutation = useUpdateCampaignMutation();
    const startMutation = useStartCampaignMutation();
    const pauseMutation = usePauseCampaignMutation();
    const resumeMutation = useResumeCampaignMutation();
    const cancelMutation = useCancelCampaignMutation();
    const scheduleMutation = useScheduleCampaignMutation();
    const populateMutation = usePopulateRecipientsMutation();
    const testSendMutation = useTestSendMutation();

    // Handlers
    const handleUpdate = async () => {
        try {
            const values = await form.validateFields();
            await updateMutation.mutateAsync({
                campaignId: campaignId!,
                data: values,
            });
            message.success('Campaign updated');
            setEditModalVisible(false);
            refetch();
        } catch (error) {
            if (error && typeof error === 'object' && 'errorFields' in error) return;
            message.error(getErrorMessage(error));
        }
    };

    const handleStart = async () => {
        try {
            await startMutation.mutateAsync(campaignId!);
            message.success('Campaign started');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handlePause = async () => {
        try {
            await pauseMutation.mutateAsync(campaignId!);
            message.success('Campaign paused');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleResume = async () => {
        try {
            await resumeMutation.mutateAsync(campaignId!);
            message.success('Campaign resumed');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleCancel = async () => {
        Modal.confirm({
            title: 'Cancel Campaign',
            content: 'Are you sure you want to cancel this campaign? This cannot be undone.',
            okText: 'Cancel Campaign',
            okType: 'danger',
            onOk: async () => {
                try {
                    await cancelMutation.mutateAsync(campaignId!);
                    message.success('Campaign cancelled');
                    refetch();
                } catch (error) {
                    message.error(getErrorMessage(error));
                }
            },
        });
    };

    const handleSchedule = async () => {
        try {
            const values = await scheduleForm.validateFields();
            await scheduleMutation.mutateAsync({
                campaignId: campaignId!,
                scheduled_at: values.scheduled_at.toISOString(),
            });
            message.success('Campaign scheduled');
            setScheduleModalVisible(false);
            scheduleForm.resetFields();
            refetch();
        } catch (error) {
            if (error && typeof error === 'object' && 'errorFields' in error) return;
            message.error(getErrorMessage(error));
        }
    };

    const handlePopulateRecipients = async () => {
        try {
            const result = await populateMutation.mutateAsync(campaignId!);
            message.success(`Added ${result.count} recipients`);
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleTestSend = async () => {
        try {
            const values = await testSendForm.validateFields();
            const emails = values.emails.split(',').map((e: string) => e.trim()).filter(Boolean);
            const result = await testSendMutation.mutateAsync({
                campaignId: campaignId!,
                emails,
            });
            if (result.errors.length > 0) {
                message.warning(`Sent ${result.sent} emails. Errors: ${result.errors.join(', ')}`);
            } else {
                message.success(`Test emails sent to ${result.sent} recipients`);
            }
            setTestSendModalVisible(false);
            testSendForm.resetFields();
        } catch (error) {
            if (error && typeof error === 'object' && 'errorFields' in error) return;
            message.error(getErrorMessage(error));
        }
    };

    const openEditModal = () => {
        if (campaign) {
            form.setFieldsValue({
                name: campaign.name,
                description: campaign.description,
                template_id: campaign.template_id,
            });
            setEditModalVisible(true);
        }
    };

    // Recipient table columns
    const recipientColumns: ColumnsType<CampaignRecipient> = [
        {
            title: 'Email',
            dataIndex: 'email',
            key: 'email',
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status: RecipientStatus) => (
                <Tag color={recipientStatusColors[status]}>{status.toUpperCase()}</Tag>
            ),
        },
        {
            title: 'Sent',
            dataIndex: 'sent_at',
            key: 'sent_at',
            render: (date: string | undefined) => (date ? dayjs(date).format('MMM D, HH:mm') : '-'),
        },
        {
            title: 'Opened',
            dataIndex: 'opened_at',
            key: 'opened_at',
            render: (date: string | undefined, record) => (
                <span>
                    {date ? dayjs(date).format('MMM D, HH:mm') : '-'}
                    {record.open_count > 1 && <Text type='secondary'> ({record.open_count}x)</Text>}
                </span>
            ),
        },
        {
            title: 'Clicked',
            dataIndex: 'clicked_at',
            key: 'clicked_at',
            render: (date: string | undefined, record) => (
                <span>
                    {date ? dayjs(date).format('MMM D, HH:mm') : '-'}
                    {record.click_count > 1 && <Text type='secondary'> ({record.click_count}x)</Text>}
                </span>
            ),
        },
        {
            title: 'Error',
            dataIndex: 'error_message',
            key: 'error_message',
            render: (error: string | undefined) =>
                error ? (
                    <Tooltip title={error}>
                        <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
                    </Tooltip>
                ) : null,
        },
    ];

    if (isLoading) {
        return (
            <div style={{ textAlign: 'center', padding: 100 }}>
                <Spin size='large' />
            </div>
        );
    }

    if (!campaign) {
        return (
            <Alert
                type='error'
                message='Campaign not found'
                description='The campaign you are looking for does not exist.'
                showIcon
            />
        );
    }

    const isDraft = campaign.status === 'draft';
    const isActive = campaign.status === 'active';
    const isPaused = campaign.status === 'paused';
    const isScheduled = campaign.status === 'scheduled';
    const canEdit = isDraft;
    const canStart = isDraft || isScheduled;
    const canPause = isActive;
    const canResume = isPaused;
    const canCancel = isActive || isPaused || isScheduled;

    // Calculate rates
    const deliveryRate = campaign.total_sent > 0
        ? ((campaign.total_delivered / campaign.total_sent) * 100).toFixed(1)
        : '0';
    const openRate = campaign.total_sent > 0
        ? ((campaign.unique_opens / campaign.total_sent) * 100).toFixed(1)
        : '0';
    const clickRate = campaign.total_sent > 0
        ? ((campaign.unique_clicks / campaign.total_sent) * 100).toFixed(1)
        : '0';
    const bounceRate = campaign.total_sent > 0
        ? ((campaign.total_bounced / campaign.total_sent) * 100).toFixed(1)
        : '0';

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: 24 }}>
                <Button
                    type='text'
                    icon={<ArrowLeftOutlined />}
                    onClick={() => navigate('/campaigns')}
                    style={{ marginBottom: 16 }}
                >
                    Back to Campaigns
                </Button>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                        <Space align='center' style={{ marginBottom: 8 }}>
                            <Title level={2} style={{ margin: 0 }}>
                                {campaign.name}
                            </Title>
                            <Tag color={statusColors[campaign.status as CampaignStatus]}>
                                {statusLabels[campaign.status as CampaignStatus]}
                            </Tag>
                        </Space>
                        {campaign.description && (
                            <Paragraph type='secondary'>{campaign.description}</Paragraph>
                        )}
                    </div>

                    <Space>
                        {canEdit && (
                            <Button icon={<EditOutlined />} onClick={openEditModal}>
                                Edit
                            </Button>
                        )}
                        {isDraft && (
                            <>
                                <Button
                                    icon={<SendOutlined />}
                                    onClick={() => setTestSendModalVisible(true)}
                                >
                                    Test Send
                                </Button>
                                <Button
                                    icon={<ScheduleOutlined />}
                                    onClick={() => setScheduleModalVisible(true)}
                                >
                                    Schedule
                                </Button>
                            </>
                        )}
                        {canStart && (
                            <Button
                                type='primary'
                                icon={<PlayCircleOutlined />}
                                onClick={handleStart}
                                loading={startMutation.isPending}
                            >
                                Start Now
                            </Button>
                        )}
                        {canPause && (
                            <Button
                                icon={<PauseCircleOutlined />}
                                onClick={handlePause}
                                loading={pauseMutation.isPending}
                            >
                                Pause
                            </Button>
                        )}
                        {canResume && (
                            <Button
                                type='primary'
                                icon={<PlayCircleOutlined />}
                                onClick={handleResume}
                                loading={resumeMutation.isPending}
                            >
                                Resume
                            </Button>
                        )}
                        {canCancel && (
                            <Button
                                danger
                                icon={<StopOutlined />}
                                onClick={handleCancel}
                                loading={cancelMutation.isPending}
                            >
                                Cancel
                            </Button>
                        )}
                    </Space>
                </div>
            </div>

            {/* Progress Bar for Active Campaigns */}
            {(isActive || isPaused) && campaign.total_recipients > 0 && (
                <Card style={{ marginBottom: 24 }}>
                    <div style={{ marginBottom: 8 }}>
                        <Text strong>Sending Progress</Text>
                        <Text type='secondary' style={{ float: 'right' }}>
                            {campaign.total_sent.toLocaleString()} / {campaign.total_recipients.toLocaleString()} sent
                        </Text>
                    </div>
                    <Progress
                        percent={Math.round((campaign.total_sent / campaign.total_recipients) * 100)}
                        status={isActive ? 'active' : undefined}
                    />
                </Card>
            )}

            {/* Stats Cards */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={4}>
                    <Card>
                        <Statistic
                            title='Recipients'
                            value={campaign.total_recipients}
                            prefix={<UserOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card>
                        <Statistic
                            title='Sent'
                            value={campaign.total_sent}
                            prefix={<SendOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card>
                        <Statistic
                            title='Delivered'
                            value={campaign.total_delivered}
                            suffix={<Text type='secondary' style={{ fontSize: 14 }}>({deliveryRate}%)</Text>}
                            prefix={<CheckCircleOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card>
                        <Statistic
                            title='Opens'
                            value={campaign.unique_opens}
                            suffix={<Text type='secondary' style={{ fontSize: 14 }}>({openRate}%)</Text>}
                            prefix={<EyeOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card>
                        <Statistic
                            title='Clicks'
                            value={campaign.unique_clicks}
                            suffix={<Text type='secondary' style={{ fontSize: 14 }}>({clickRate}%)</Text>}
                            prefix={<MailOutlined />}
                            valueStyle={{ color: '#1890ff' }}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card>
                        <Statistic
                            title='Bounced'
                            value={campaign.total_bounced}
                            suffix={<Text type='secondary' style={{ fontSize: 14 }}>({bounceRate}%)</Text>}
                            prefix={<CloseCircleOutlined />}
                            valueStyle={{ color: '#ff4d4f' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* Tabs */}
            <Card>
                <Tabs
                    items={[
                        {
                            key: 'recipients',
                            label: 'Recipients',
                            children: (
                                <div>
                                    <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                                        <Space>
                                            <Text>Status:</Text>
                                            <Select
                                                style={{ width: 150 }}
                                                placeholder='All statuses'
                                                allowClear
                                                value={recipientStatus}
                                                onChange={setRecipientStatus}
                                                options={[
                                                    { value: 'pending', label: 'Pending' },
                                                    { value: 'queued', label: 'Queued' },
                                                    { value: 'sent', label: 'Sent' },
                                                    { value: 'delivered', label: 'Delivered' },
                                                    { value: 'opened', label: 'Opened' },
                                                    { value: 'clicked', label: 'Clicked' },
                                                    { value: 'bounced', label: 'Bounced' },
                                                    { value: 'failed', label: 'Failed' },
                                                ]}
                                            />
                                        </Space>
                                        {isDraft && (
                                            <Button
                                                type='primary'
                                                onClick={handlePopulateRecipients}
                                                loading={populateMutation.isPending}
                                            >
                                                Populate Recipients
                                            </Button>
                                        )}
                                    </div>
                                    <Table
                                        columns={recipientColumns}
                                        dataSource={recipientsData?.items}
                                        rowKey='id'
                                        loading={recipientsLoading}
                                        pagination={{
                                            current: recipientPage,
                                            pageSize: 50,
                                            total: recipientsData?.total,
                                            showTotal: (total) => `${total} recipients`,
                                            onChange: setRecipientPage,
                                        }}
                                    />
                                </div>
                            ),
                        },
                        {
                            key: 'details',
                            label: 'Details',
                            children: (
                                <Descriptions column={2} bordered>
                                    <Descriptions.Item label='Campaign Type'>
                                        {campaign.campaign_type === 'ab_test' ? 'A/B Test' : 'Standard'}
                                    </Descriptions.Item>
                                    <Descriptions.Item label='Status'>
                                        <Tag color={statusColors[campaign.status as CampaignStatus]}>
                                            {statusLabels[campaign.status as CampaignStatus]}
                                        </Tag>
                                    </Descriptions.Item>
                                    <Descriptions.Item label='Created'>
                                        {dayjs(campaign.created_at).format('MMM D, YYYY h:mm A')}
                                    </Descriptions.Item>
                                    <Descriptions.Item label='Last Updated'>
                                        {dayjs(campaign.updated_at).format('MMM D, YYYY h:mm A')}
                                    </Descriptions.Item>
                                    {campaign.scheduled_at && (
                                        <Descriptions.Item label='Scheduled For'>
                                            {dayjs(campaign.scheduled_at).format('MMM D, YYYY h:mm A')}
                                        </Descriptions.Item>
                                    )}
                                    {campaign.started_at && (
                                        <Descriptions.Item label='Started At'>
                                            {dayjs(campaign.started_at).format('MMM D, YYYY h:mm A')}
                                        </Descriptions.Item>
                                    )}
                                    {campaign.completed_at && (
                                        <Descriptions.Item label='Completed At'>
                                            {dayjs(campaign.completed_at).format('MMM D, YYYY h:mm A')}
                                        </Descriptions.Item>
                                    )}
                                    <Descriptions.Item label='Send Rate'>
                                        {campaign.send_rate_per_hour || 'Default'} /hour
                                    </Descriptions.Item>
                                    {campaign.from_email_override && (
                                        <Descriptions.Item label='From Email'>
                                            {campaign.from_email_override}
                                        </Descriptions.Item>
                                    )}
                                    {campaign.from_name_override && (
                                        <Descriptions.Item label='From Name'>
                                            {campaign.from_name_override}
                                        </Descriptions.Item>
                                    )}
                                </Descriptions>
                            ),
                        },
                        {
                            key: 'analytics',
                            label: 'Analytics',
                            children: analytics ? (
                                <div>
                                    <Row gutter={[16, 16]}>
                                        <Col span={6}>
                                            <Card size='small'>
                                                <Statistic
                                                    title='Delivery Rate'
                                                    value={analytics.delivery_rate}
                                                    suffix='%'
                                                    precision={1}
                                                />
                                            </Card>
                                        </Col>
                                        <Col span={6}>
                                            <Card size='small'>
                                                <Statistic
                                                    title='Open Rate'
                                                    value={analytics.open_rate}
                                                    suffix='%'
                                                    precision={1}
                                                    valueStyle={{ color: '#52c41a' }}
                                                />
                                            </Card>
                                        </Col>
                                        <Col span={6}>
                                            <Card size='small'>
                                                <Statistic
                                                    title='Click Rate'
                                                    value={analytics.click_rate}
                                                    suffix='%'
                                                    precision={1}
                                                    valueStyle={{ color: '#1890ff' }}
                                                />
                                            </Card>
                                        </Col>
                                        <Col span={6}>
                                            <Card size='small'>
                                                <Statistic
                                                    title='Bounce Rate'
                                                    value={analytics.bounce_rate}
                                                    suffix='%'
                                                    precision={1}
                                                    valueStyle={{ color: analytics.bounce_rate > 5 ? '#ff4d4f' : undefined }}
                                                />
                                            </Card>
                                        </Col>
                                    </Row>

                                    <Divider />

                                    <Row gutter={[16, 16]}>
                                        <Col span={8}>
                                            <Card size='small' title='Unique Opens'>
                                                <Statistic value={analytics.unique_opens} />
                                                <Text type='secondary'>
                                                    {analytics.unique_open_rate.toFixed(1)}% of delivered
                                                </Text>
                                            </Card>
                                        </Col>
                                        <Col span={8}>
                                            <Card size='small' title='Unique Clicks'>
                                                <Statistic value={analytics.unique_clicks} />
                                                <Text type='secondary'>
                                                    {analytics.unique_click_rate.toFixed(1)}% of delivered
                                                </Text>
                                            </Card>
                                        </Col>
                                        <Col span={8}>
                                            <Card size='small' title='Unsubscribes'>
                                                <Statistic
                                                    value={analytics.total_unsubscribed}
                                                    valueStyle={{ color: analytics.total_unsubscribed > 0 ? '#faad14' : undefined }}
                                                />
                                                <Text type='secondary'>
                                                    {analytics.unsubscribe_rate.toFixed(2)}% of sent
                                                </Text>
                                            </Card>
                                        </Col>
                                    </Row>
                                </div>
                            ) : (
                                <div style={{ textAlign: 'center', padding: 40 }}>
                                    <Text type='secondary'>No analytics data available yet</Text>
                                </div>
                            ),
                        },
                    ]}
                />
            </Card>

            {/* Edit Modal */}
            <Modal
                title='Edit Campaign'
                open={editModalVisible}
                onOk={handleUpdate}
                onCancel={() => setEditModalVisible(false)}
                confirmLoading={updateMutation.isPending}
            >
                <Form form={form} layout='vertical'>
                    <Form.Item
                        name='name'
                        label='Campaign Name'
                        rules={[{ required: true, message: 'Please enter a campaign name' }]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item name='description' label='Description'>
                        <Input.TextArea rows={2} />
                    </Form.Item>
                    <Form.Item
                        name='template_id'
                        label='Email Template'
                        rules={[{ required: true, message: 'Please select a template' }]}
                    >
                        <Select
                            options={templatesData?.items.map((t) => ({
                                value: t.id,
                                label: t.name,
                            }))}
                        />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Schedule Modal */}
            <Modal
                title='Schedule Campaign'
                open={scheduleModalVisible}
                onOk={handleSchedule}
                onCancel={() => {
                    setScheduleModalVisible(false);
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

            {/* Test Send Modal */}
            <Modal
                title='Send Test Email'
                open={testSendModalVisible}
                onOk={handleTestSend}
                onCancel={() => {
                    setTestSendModalVisible(false);
                    testSendForm.resetFields();
                }}
                confirmLoading={testSendMutation.isPending}
            >
                <Form form={testSendForm} layout='vertical'>
                    <Form.Item
                        name='emails'
                        label='Email Addresses'
                        rules={[{ required: true, message: 'Please enter at least one email address' }]}
                        help='Enter email addresses separated by commas'
                    >
                        <Input.TextArea
                            rows={3}
                            placeholder='test@example.com, another@example.com'
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
