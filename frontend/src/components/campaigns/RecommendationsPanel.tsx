import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Card,
    List,
    Tag,
    Button,
    Space,
    Typography,
    Modal,
    Form,
    Input,
    Select,
    message,
    Empty,
    Badge,
    Tooltip,
    Statistic,
} from 'antd';
import {
    RocketOutlined,
    CloseOutlined,
    TrendingUpOutlined,
    BulbOutlined,
    UserOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
} from '@ant-design/icons';
import {
    CampaignRecommendation,
    TriggerType,
    useRecommendationsQuery,
    useDismissRecommendationMutation,
    useConvertRecommendationMutation,
} from '../../services/recommendationService';
import { useEmailTemplatesQuery } from '../../services/emailService';
import { getErrorMessage } from '../../services/api';

const { Text, Paragraph } = Typography;

// Trigger type icons and colors
const triggerConfig: Record<TriggerType, { icon: React.ReactNode; color: string; label: string }> = {
    trending_topic: {
        icon: <TrendingUpOutlined />,
        color: 'blue',
        label: 'Trending Topic',
    },
    sentiment_shift: {
        icon: <BulbOutlined />,
        color: 'gold',
        label: 'Sentiment Shift',
    },
    engagement_spike: {
        icon: <RocketOutlined />,
        color: 'green',
        label: 'Engagement Spike',
    },
};

interface RecommendationsPanelProps {
    maxItems?: number;
    showHeader?: boolean;
}

export default function RecommendationsPanel({
    maxItems = 5,
    showHeader = true,
}: RecommendationsPanelProps) {
    const navigate = useNavigate();
    const [convertModal, setConvertModal] = useState<{
        visible: boolean;
        recommendation?: CampaignRecommendation;
    }>({ visible: false });
    const [form] = Form.useForm();

    // Queries
    const { data, isLoading, refetch } = useRecommendationsQuery(1, maxItems, 'active');
    const { data: templatesData } = useEmailTemplatesQuery(true);

    // Mutations
    const dismissMutation = useDismissRecommendationMutation();
    const convertMutation = useConvertRecommendationMutation();

    // Handlers
    const handleDismiss = async (id: string) => {
        try {
            await dismissMutation.mutateAsync(id);
            message.success('Recommendation dismissed');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleConvert = async () => {
        try {
            const values = await form.validateFields();
            if (convertModal.recommendation) {
                const result = await convertMutation.mutateAsync({
                    id: convertModal.recommendation.id,
                    campaign_name: values.campaign_name,
                    template_id: values.template_id,
                });
                message.success('Campaign created from recommendation');
                setConvertModal({ visible: false });
                form.resetFields();
                navigate(`/campaigns/${result.campaign_id}`);
            }
        } catch (error) {
            if (error && typeof error === 'object' && 'errorFields' in error) return;
            message.error(getErrorMessage(error));
        }
    };

    const openConvertModal = (recommendation: CampaignRecommendation) => {
        form.setFieldsValue({
            campaign_name: `Campaign: ${recommendation.title}`,
        });
        setConvertModal({ visible: true, recommendation });
    };

    if (!data?.items.length && !isLoading) {
        return null; // Don't show empty panel
    }

    return (
        <>
            <Card
                title={
                    showHeader && (
                        <Space>
                            <BulbOutlined />
                            <span>Campaign Recommendations</span>
                            {data?.total ? (
                                <Badge count={data.total} style={{ backgroundColor: '#52c41a' }} />
                            ) : null}
                        </Space>
                    )
                }
                extra={
                    showHeader && data?.total && data.total > maxItems ? (
                        <Button type='link' onClick={() => navigate('/recommendations')}>
                            View All
                        </Button>
                    ) : null
                }
                loading={isLoading}
                size='small'
            >
                {data?.items.length === 0 ? (
                    <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description='No recommendations at this time'
                    />
                ) : (
                    <List
                        dataSource={data?.items}
                        renderItem={(item) => {
                            const config = triggerConfig[item.trigger_type];
                            const changePositive = item.trend_data.change_percent > 0;

                            return (
                                <List.Item
                                    key={item.id}
                                    actions={[
                                        <Tooltip title='Create Campaign' key='create'>
                                            <Button
                                                type='primary'
                                                size='small'
                                                icon={<RocketOutlined />}
                                                onClick={() => openConvertModal(item)}
                                            >
                                                Create
                                            </Button>
                                        </Tooltip>,
                                        <Tooltip title='Dismiss' key='dismiss'>
                                            <Button
                                                size='small'
                                                icon={<CloseOutlined />}
                                                onClick={() => handleDismiss(item.id)}
                                            />
                                        </Tooltip>,
                                    ]}
                                >
                                    <List.Item.Meta
                                        avatar={
                                            <Tag color={config.color} icon={config.icon}>
                                                {config.label}
                                            </Tag>
                                        }
                                        title={<Text strong>{item.title}</Text>}
                                        description={
                                            <Space direction='vertical' size={4} style={{ width: '100%' }}>
                                                <Paragraph
                                                    type='secondary'
                                                    ellipsis={{ rows: 2 }}
                                                    style={{ marginBottom: 4 }}
                                                >
                                                    {item.description}
                                                </Paragraph>
                                                <Space split={<Text type='secondary'>|</Text>}>
                                                    <Space size={4}>
                                                        <UserOutlined />
                                                        <Text type='secondary'>
                                                            {item.suggested_audience_size.toLocaleString()} contacts
                                                        </Text>
                                                    </Space>
                                                    <Space size={4}>
                                                        {changePositive ? (
                                                            <ArrowUpOutlined style={{ color: '#52c41a' }} />
                                                        ) : (
                                                            <ArrowDownOutlined style={{ color: '#ff4d4f' }} />
                                                        )}
                                                        <Text
                                                            style={{
                                                                color: changePositive ? '#52c41a' : '#ff4d4f',
                                                            }}
                                                        >
                                                            {Math.abs(item.trend_data.change_percent).toFixed(0)}%
                                                        </Text>
                                                    </Space>
                                                    {item.topic_keywords.length > 0 && (
                                                        <Space size={4}>
                                                            {item.topic_keywords.slice(0, 3).map((kw, i) => (
                                                                <Tag key={i} style={{ margin: 0 }}>
                                                                    {kw}
                                                                </Tag>
                                                            ))}
                                                            {item.topic_keywords.length > 3 && (
                                                                <Text type='secondary'>
                                                                    +{item.topic_keywords.length - 3}
                                                                </Text>
                                                            )}
                                                        </Space>
                                                    )}
                                                </Space>
                                            </Space>
                                        }
                                    />
                                </List.Item>
                            );
                        }}
                    />
                )}
            </Card>

            {/* Convert to Campaign Modal */}
            <Modal
                title='Create Campaign from Recommendation'
                open={convertModal.visible}
                onOk={handleConvert}
                onCancel={() => {
                    setConvertModal({ visible: false });
                    form.resetFields();
                }}
                confirmLoading={convertMutation.isPending}
            >
                {convertModal.recommendation && (
                    <div style={{ marginBottom: 24 }}>
                        <Card size='small' style={{ background: '#fafafa' }}>
                            <Space direction='vertical' size={4}>
                                <Text strong>{convertModal.recommendation.title}</Text>
                                <Text type='secondary'>{convertModal.recommendation.description}</Text>
                                <Space>
                                    <Statistic
                                        title='Audience'
                                        value={convertModal.recommendation.suggested_audience_size}
                                        prefix={<UserOutlined />}
                                        valueStyle={{ fontSize: 16 }}
                                    />
                                    <Statistic
                                        title='Trend'
                                        value={Math.abs(convertModal.recommendation.trend_data.change_percent)}
                                        suffix='%'
                                        prefix={
                                            convertModal.recommendation.trend_data.change_percent > 0 ? (
                                                <ArrowUpOutlined />
                                            ) : (
                                                <ArrowDownOutlined />
                                            )
                                        }
                                        valueStyle={{
                                            fontSize: 16,
                                            color:
                                                convertModal.recommendation.trend_data.change_percent > 0
                                                    ? '#52c41a'
                                                    : '#ff4d4f',
                                        }}
                                    />
                                </Space>
                            </Space>
                        </Card>
                    </div>
                )}

                <Form form={form} layout='vertical'>
                    <Form.Item
                        name='campaign_name'
                        label='Campaign Name'
                        rules={[{ required: true, message: 'Please enter a campaign name' }]}
                    >
                        <Input placeholder='e.g., Response to Trending Topic' />
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
                </Form>
            </Modal>
        </>
    );
}
