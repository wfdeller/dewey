import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Tag,
  Space,
  Input,
  Select,
  Button,
  Card,
  Row,
  Col,
  Modal,
  Form,
  message,
  Tooltip,
  Statistic,
} from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  ReloadOutlined,
  MailOutlined,
  UserOutlined,
  TagOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  useContactsQuery,
  useCreateContactMutation,
  ContactFilters,
} from '../services/contactsService';
import { getErrorMessage } from '../services/api';
import type { Contact, ToneLabel } from '../types';

// Tone color mapping
const getToneColor = (tone: ToneLabel): string => {
  const emotionTones: Record<string, string> = {
    angry: 'red',
    frustrated: 'orange',
    grateful: 'green',
    hopeful: 'cyan',
    anxious: 'gold',
    disappointed: 'magenta',
    enthusiastic: 'lime',
    satisfied: 'green',
    confused: 'purple',
    concerned: 'volcano',
  };
  const styleTones: Record<string, string> = {
    cordial: 'blue',
    formal: 'geekblue',
    informal: 'default',
    urgent: 'red',
    demanding: 'volcano',
    polite: 'cyan',
    hostile: 'magenta',
    professional: 'blue',
    casual: 'default',
    apologetic: 'gold',
  };
  return emotionTones[tone] || styleTones[tone] || 'default';
};

// Available tone options for filtering
const TONE_OPTIONS: { value: ToneLabel; label: string }[] = [
  { value: 'grateful', label: 'Grateful' },
  { value: 'frustrated', label: 'Frustrated' },
  { value: 'angry', label: 'Angry' },
  { value: 'hopeful', label: 'Hopeful' },
  { value: 'cordial', label: 'Cordial' },
  { value: 'formal', label: 'Formal' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'professional', label: 'Professional' },
];

export default function Contacts() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState<ContactFilters>({});
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [form] = Form.useForm();

  const { data, isLoading, refetch } = useContactsQuery(page, pageSize, filters);
  const createMutation = useCreateContactMutation();

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await createMutation.mutateAsync({
        email: values.email,
        name: values.name,
        phone: values.phone,
        tags: values.tags || [],
      });
      message.success('Contact created successfully');
      setCreateModalVisible(false);
      form.resetFields();
      refetch();
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return;
      }
      message.error(getErrorMessage(error));
    }
  };

  const columns: ColumnsType<Contact> = [
    {
      title: 'Name',
      key: 'name',
      ellipsis: true,
      render: (_, record) => (
        <a onClick={() => navigate(`/contacts/${record.id}`)}>
          {record.name || record.email}
        </a>
      ),
    },
    {
      title: 'Messages',
      dataIndex: 'message_count',
      key: 'message_count',
      width: 120,
      align: 'center',
      sorter: true,
      render: (count: number) => (
        <Tag color={count > 10 ? 'blue' : 'default'}>{count}</Tag>
      ),
    },
    {
      title: 'Tones',
      dataIndex: 'dominant_tones',
      key: 'dominant_tones',
      width: 180,
      render: (tones: ToneLabel[]) => (
        <Space wrap size={[0, 4]}>
          {tones?.slice(0, 2).map((tone) => (
            <Tag key={tone} color={getToneColor(tone)}>
              {tone}
            </Tag>
          ))}
          {tones?.length > 2 && (
            <Tooltip title={tones.slice(2).join(', ')}>
              <Tag>+{tones.length - 2}</Tag>
            </Tooltip>
          )}
          {(!tones || tones.length === 0) && (
            <Tag color="default">-</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      width: 200,
      render: (tags: string[]) => (
        <Space wrap size={[0, 4]}>
          {tags?.slice(0, 3).map((tag) => (
            <Tag key={tag} icon={<TagOutlined />}>
              {tag}
            </Tag>
          ))}
          {tags?.length > 3 && (
            <Tooltip title={tags.slice(3).join(', ')}>
              <Tag>+{tags.length - 3}</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 140,
      sorter: true,
      render: (date: string) =>
        date ? dayjs(date).format('MMM D, YYYY') : '-',
    },
  ];

  // Calculate stats
  const stats = {
    total: data?.total || 0,
    withMessages: data?.items.filter((c) => c.message_count > 0).length || 0,
    withTones: data?.items.filter((c) => c.dominant_tones && c.dominant_tones.length > 0).length || 0,
  };

  return (
    <div>
      <div
        style={{
          marginBottom: 24,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h2 style={{ margin: 0 }}>Contacts</h2>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalVisible(true)}
        >
          Add Contact
        </Button>
      </div>

      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Contacts"
              value={stats.total}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="With Messages"
              value={stats.withMessages}
              prefix={<MailOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="With Tones"
              value={stats.withTones}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={8} lg={6}>
            <Input
              placeholder="Search by email or name..."
              prefix={<SearchOutlined />}
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              allowClear
            />
          </Col>

          <Col xs={24} sm={12} md={8} lg={4}>
            <Input
              placeholder="Filter by tag..."
              prefix={<TagOutlined />}
              value={filters.tag}
              onChange={(e) => setFilters({ ...filters, tag: e.target.value })}
              allowClear
            />
          </Col>

          <Col xs={24} sm={12} md={8} lg={4}>
            <Select
              placeholder="Filter by tone..."
              style={{ width: '100%' }}
              value={filters.tone}
              onChange={(value) => setFilters({ ...filters, tone: value })}
              allowClear
              options={TONE_OPTIONS}
            />
          </Col>

          <Col>
            <Space>
              <Button onClick={() => setFilters({})}>Clear Filters</Button>
              <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Contacts Table */}
      <Table
        columns={columns}
        dataSource={data?.items}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize,
          total: data?.total,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} contacts`,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
        onRow={(record) => ({
          onClick: () => navigate(`/contacts/${record.id}`),
          style: { cursor: 'pointer' },
        })}
      />

      {/* Create Contact Modal */}
      <Modal
        title="Add Contact"
        open={createModalVisible}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
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
            <Input placeholder="contact@example.com" />
          </Form.Item>

          <Form.Item name="name" label="Name">
            <Input placeholder="John Doe" />
          </Form.Item>

          <Form.Item name="phone" label="Phone">
            <Input placeholder="+1 (555) 123-4567" />
          </Form.Item>

          <Form.Item name="tags" label="Tags">
            <Select mode="tags" placeholder="Add tags..." tokenSeparators={[',']} />
          </Form.Item>
        </Form>
      </Modal>

    </div>
  );
}
