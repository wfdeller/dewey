import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography,
  Card,
  Descriptions,
  Table,
  Tag,
  Space,
  Button,
  Spin,
  Empty,
  Row,
  Col,
  Statistic,
  Form,
  Input,
  Modal,
  message,
  Popconfirm,
  Tabs,
} from 'antd';
import {
  ArrowLeftOutlined,
  MailOutlined,
  PhoneOutlined,
  TagOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { Line } from '@ant-design/charts';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  useContactQuery,
  useContactMessagesQuery,
  useContactTimelineQuery,
  useUpdateContactMutation,
  useDeleteContactMutation,
  useAddTagMutation,
  useRemoveTagMutation,
  ContactMessageSummary,
} from '../services/contactsService';
import { getErrorMessage } from '../services/api';
import type { SentimentLabel } from '../types';

const { Title, Text, Paragraph } = Typography;

const sentimentColors: Record<SentimentLabel, string> = {
  positive: 'green',
  neutral: 'gold',
  negative: 'red',
};

export default function ContactDetail() {
  const { contactId } = useParams<{ contactId: string }>();
  const navigate = useNavigate();
  const [messagesPage, setMessagesPage] = useState(1);
  const [messagesPageSize, setMessagesPageSize] = useState(10);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [newTag, setNewTag] = useState('');
  const [form] = Form.useForm();

  const { data: contact, isLoading, refetch } = useContactQuery(contactId || '');
  const { data: messagesData, isLoading: messagesLoading } = useContactMessagesQuery(
    contactId || '',
    messagesPage,
    messagesPageSize
  );
  const { data: timelineData } = useContactTimelineQuery(contactId || '', 90);

  const updateMutation = useUpdateContactMutation();
  const deleteMutation = useDeleteContactMutation();
  const addTagMutation = useAddTagMutation();
  const removeTagMutation = useRemoveTagMutation();

  const handleEdit = async () => {
    try {
      const values = await form.validateFields();
      await updateMutation.mutateAsync({
        contactId: contactId!,
        data: {
          name: values.name,
          email: values.email,
          phone: values.phone,
          notes: values.notes,
        },
      });
      message.success('Contact updated successfully');
      setEditModalVisible(false);
      refetch();
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return;
      }
      message.error(getErrorMessage(error));
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(contactId!);
      message.success('Contact deleted successfully');
      navigate('/contacts');
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  const handleAddTag = async () => {
    if (!newTag.trim()) return;
    try {
      await addTagMutation.mutateAsync({
        contactId: contactId!,
        tag: newTag.trim(),
      });
      setNewTag('');
      refetch();
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  const handleRemoveTag = async (tag: string) => {
    try {
      await removeTagMutation.mutateAsync({
        contactId: contactId!,
        tag,
      });
      refetch();
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  const messageColumns: ColumnsType<ContactMessageSummary> = [
    {
      title: 'Subject',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
      render: (text: string, record) => (
        <a onClick={() => navigate(`/messages/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: 'Source',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (source: string) => (
        <Tag color={source === 'email' ? 'blue' : source === 'form' ? 'purple' : 'cyan'}>
          {source.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Sentiment',
      dataIndex: 'sentiment_label',
      key: 'sentiment_label',
      width: 100,
      render: (label: SentimentLabel | undefined) => {
        if (!label) return <Tag>Pending</Tag>;
        return (
          <Tag color={sentimentColors[label]}>
            {label.charAt(0).toUpperCase() + label.slice(1)}
          </Tag>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'processing_status',
      key: 'processing_status',
      width: 100,
      render: (status: string) => {
        const colors: Record<string, string> = {
          pending: 'default',
          processing: 'processing',
          completed: 'success',
          failed: 'error',
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      },
    },
    {
      title: 'Received',
      dataIndex: 'received_at',
      key: 'received_at',
      width: 150,
      render: (date: string) => dayjs(date).format('MMM D, YYYY HH:mm'),
    },
  ];

  // Prepare chart data
  const chartData = timelineData?.entries.map((entry) => ({
    date: entry.date,
    sentiment: entry.avg_sentiment ?? 0,
    messages: entry.message_count,
  })) || [];

  const chartConfig = {
    data: chartData,
    xField: 'date',
    yField: 'sentiment',
    smooth: true,
    height: 200,
    xAxis: {
      label: {
        formatter: (v: string) => dayjs(v).format('MMM D'),
      },
    },
    yAxis: {
      min: -1,
      max: 1,
      label: {
        formatter: (v: number) => {
          if (v > 0.3) return 'Positive';
          if (v < -0.3) return 'Negative';
          return 'Neutral';
        },
      },
    },
    tooltip: {
      formatter: (datum: { date: string; sentiment: number; messages: number }) => ({
        name: 'Sentiment',
        value: datum.sentiment.toFixed(2),
      }),
    },
    annotations: [
      {
        type: 'line',
        start: ['min', 0.3],
        end: ['max', 0.3],
        style: { stroke: '#52c41a', lineDash: [4, 4] },
      },
      {
        type: 'line',
        start: ['min', -0.3],
        end: ['max', -0.3],
        style: { stroke: '#ff4d4f', lineDash: [4, 4] },
      },
    ],
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!contact) {
    return (
      <Empty description="Contact not found">
        <Button onClick={() => navigate('/contacts')}>Back to Contacts</Button>
      </Empty>
    );
  }

  const getSentimentColor = (score: number | undefined): string => {
    if (score === undefined || score === null) return 'default';
    if (score > 0.3) return '#52c41a';
    if (score < -0.3) return '#ff4d4f';
    return '#faad14';
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/contacts')}
          style={{ marginBottom: 8 }}
        >
          Back to Contacts
        </Button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              {contact.name || contact.email}
            </Title>
            {contact.name && (
              <Text type="secondary">{contact.email}</Text>
            )}
          </div>
          <Space>
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                form.setFieldsValue({
                  name: contact.name,
                  email: contact.email,
                  phone: contact.phone,
                  notes: contact.notes,
                });
                setEditModalVisible(true);
              }}
            >
              Edit
            </Button>
            <Popconfirm
              title="Delete this contact?"
              description="Messages will be preserved but unlinked."
              onConfirm={handleDelete}
              okText="Delete"
              okType="danger"
            >
              <Button danger icon={<DeleteOutlined />}>
                Delete
              </Button>
            </Popconfirm>
          </Space>
        </div>
      </div>

      <Row gutter={24}>
        {/* Left Column - Contact Info */}
        <Col xs={24} lg={8}>
          {/* Basic Info Card */}
          <Card title="Contact Information" style={{ marginBottom: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label={<><MailOutlined /> Email</>}>
                <Text copyable>{contact.email}</Text>
              </Descriptions.Item>
              {contact.phone && (
                <Descriptions.Item label={<><PhoneOutlined /> Phone</>}>
                  {contact.phone}
                </Descriptions.Item>
              )}
              {contact.address && (
                <Descriptions.Item label="Address">
                  {[
                    contact.address.street,
                    contact.address.city,
                    contact.address.state,
                    contact.address.zip,
                  ]
                    .filter(Boolean)
                    .join(', ')}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Created">
                {contact.created_at
                  ? dayjs(contact.created_at).format('MMM D, YYYY')
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="First Contact">
                {contact.first_contact_at
                  ? dayjs(contact.first_contact_at).format('MMM D, YYYY')
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Last Contact">
                {contact.last_contact_at
                  ? dayjs(contact.last_contact_at).format('MMM D, YYYY')
                  : '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* Stats Card */}
          <Card title="Statistics" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Messages"
                  value={contact.message_count}
                  prefix={<MailOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Avg Sentiment"
                  value={
                    contact.avg_sentiment != null
                      ? contact.avg_sentiment.toFixed(2)
                      : 'N/A'
                  }
                  valueStyle={{ color: getSentimentColor(contact.avg_sentiment) }}
                />
              </Col>
            </Row>
          </Card>

          {/* Tags Card */}
          <Card
            title={<><TagOutlined /> Tags</>}
            style={{ marginBottom: 16 }}
          >
            <Space wrap style={{ marginBottom: 12 }}>
              {contact.tags?.map((tag) => (
                <Tag
                  key={tag}
                  closable
                  onClose={() => handleRemoveTag(tag)}
                >
                  {tag}
                </Tag>
              ))}
              {(!contact.tags || contact.tags.length === 0) && (
                <Text type="secondary">No tags</Text>
              )}
            </Space>
            <Input
              placeholder="Add tag..."
              prefix={<PlusOutlined />}
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onPressEnter={handleAddTag}
              suffix={
                newTag && (
                  <CloseOutlined
                    style={{ cursor: 'pointer' }}
                    onClick={() => setNewTag('')}
                  />
                )
              }
            />
          </Card>

          {/* Custom Fields Card */}
          {contact.custom_fields && contact.custom_fields.length > 0 && (
            <Card title="Custom Fields" style={{ marginBottom: 16 }}>
              <Descriptions column={1} size="small">
                {contact.custom_fields.map((field) => (
                  <Descriptions.Item key={field.field_key} label={field.field_name}>
                    {field.field_type === 'boolean'
                      ? field.value
                        ? 'Yes'
                        : 'No'
                      : Array.isArray(field.value)
                      ? field.value.join(', ')
                      : String(field.value ?? '-')}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </Card>
          )}

          {/* Notes Card */}
          {contact.notes && (
            <Card title="Notes" style={{ marginBottom: 16 }}>
              <Paragraph>{contact.notes}</Paragraph>
            </Card>
          )}
        </Col>

        {/* Right Column - Activity */}
        <Col xs={24} lg={16}>
          <Tabs
            items={[
              {
                key: 'messages',
                label: `Messages (${messagesData?.total || 0})`,
                children: (
                  <Card>
                    <Table
                      columns={messageColumns}
                      dataSource={messagesData?.items}
                      rowKey="id"
                      loading={messagesLoading}
                      pagination={{
                        current: messagesPage,
                        pageSize: messagesPageSize,
                        total: messagesData?.total,
                        showSizeChanger: true,
                        showTotal: (total) => `${total} messages`,
                        onChange: (p, ps) => {
                          setMessagesPage(p);
                          setMessagesPageSize(ps);
                        },
                      }}
                      onRow={(record) => ({
                        onClick: () => navigate(`/messages/${record.id}`),
                        style: { cursor: 'pointer' },
                      })}
                    />
                  </Card>
                ),
              },
              {
                key: 'timeline',
                label: 'Sentiment Timeline',
                children: (
                  <Card>
                    {chartData.length > 0 ? (
                      <>
                        <Paragraph type="secondary" style={{ marginBottom: 16 }}>
                          Sentiment trend over the last 90 days
                        </Paragraph>
                        <Line {...chartConfig} />
                      </>
                    ) : (
                      <Empty description="No timeline data available" />
                    )}
                  </Card>
                ),
              },
            ]}
          />
        </Col>
      </Row>

      {/* Edit Modal */}
      <Modal
        title="Edit Contact"
        open={editModalVisible}
        onOk={handleEdit}
        onCancel={() => {
          setEditModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={updateMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Email is required' },
              { type: 'email', message: 'Please enter a valid email' },
            ]}
          >
            <Input />
          </Form.Item>

          <Form.Item name="name" label="Name">
            <Input />
          </Form.Item>

          <Form.Item name="phone" label="Phone">
            <Input />
          </Form.Item>

          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
