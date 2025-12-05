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
import type { Contact } from '../types';

// Sentiment indicator colors
const getSentimentColor = (score: number | undefined): string => {
  if (score === undefined || score === null) return 'default';
  if (score > 0.3) return 'green';
  if (score < -0.3) return 'red';
  return 'gold';
};

const getSentimentLabel = (score: number | undefined): string => {
  if (score === undefined || score === null) return 'N/A';
  if (score > 0.3) return 'Positive';
  if (score < -0.3) return 'Negative';
  return 'Neutral';
};

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
      title: 'Sentiment',
      dataIndex: 'avg_sentiment',
      key: 'avg_sentiment',
      width: 120,
      align: 'center',
      render: (score: number | undefined) => (
        <Tag color={getSentimentColor(score)}>{getSentimentLabel(score)}</Tag>
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
    positive:
      data?.items.filter((c) => c.avg_sentiment && c.avg_sentiment > 0.3)
        .length || 0,
    negative:
      data?.items.filter((c) => c.avg_sentiment && c.avg_sentiment < -0.3)
        .length || 0,
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
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Contacts"
              value={stats.total}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="With Messages"
              value={stats.withMessages}
              prefix={<MailOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Positive Sentiment"
              value={stats.positive}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Negative Sentiment"
              value={stats.negative}
              valueStyle={{ color: '#ff4d4f' }}
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
              placeholder="Sentiment"
              style={{ width: '100%' }}
              value={filters.sentiment}
              onChange={(value) => setFilters({ ...filters, sentiment: value })}
              allowClear
              options={[
                { value: 'positive', label: 'Positive' },
                { value: 'neutral', label: 'Neutral' },
                { value: 'negative', label: 'Negative' },
              ]}
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
