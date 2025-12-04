import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Tag,
  Space,
  Input,
  Select,
  DatePicker,
  Button,
  Card,
  Row,
  Col,
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useMessages } from '../hooks/useMessages';
import { useUIStore } from '../stores';
import type { Message, SentimentLabel, MessageSource } from '../types';

const { RangePicker } = DatePicker;

const sentimentColors: Record<SentimentLabel, string> = {
  positive: 'green',
  neutral: 'gold',
  negative: 'red',
};

const sourceColors: Record<MessageSource, string> = {
  email: 'blue',
  form: 'purple',
  api: 'cyan',
  upload: 'orange',
};

export default function Messages() {
  const navigate = useNavigate();
  const { messageFilters, setMessageFilters } = useUIStore();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const { data, isLoading, refetch } = useMessages({
    page,
    pageSize,
    ...messageFilters,
  });

  const columns: ColumnsType<Message> = [
    {
      title: 'Subject',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
      render: (text: string, record: Message) => (
        <a onClick={() => navigate(`/messages/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: 'Sender',
      dataIndex: 'senderEmail',
      key: 'senderEmail',
      ellipsis: true,
      width: 200,
      render: (email: string, record: Message) => (
        <span>{record.senderName || email}</span>
      ),
    },
    {
      title: 'Source',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (source: MessageSource) => (
        <Tag color={sourceColors[source]}>{source.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Sentiment',
      key: 'sentiment',
      width: 100,
      render: (_: unknown, record: Message) => {
        const label = record.analysis?.sentimentLabel;
        if (!label) return <Tag>Pending</Tag>;
        return (
          <Tag color={sentimentColors[label]}>
            {label.charAt(0).toUpperCase() + label.slice(1)}
          </Tag>
        );
      },
    },
    {
      title: 'Campaign',
      key: 'campaign',
      width: 100,
      render: (_: unknown, record: Message) => (
        record.isTemplateMatch ? (
          <Tag color="volcano">Campaign</Tag>
        ) : null
      ),
    },
    {
      title: 'Received',
      dataIndex: 'receivedAt',
      key: 'receivedAt',
      width: 150,
      render: (date: string) => dayjs(date).format('MMM D, YYYY HH:mm'),
      sorter: true,
    },
    {
      title: 'Status',
      dataIndex: 'processingStatus',
      key: 'processingStatus',
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
  ];

  // Mock data for development
  const mockData: Message[] = [
    {
      id: '1',
      tenantId: '1',
      subject: 'Question about my account',
      bodyText: 'Hello, I have a question...',
      senderEmail: 'john@example.com',
      senderName: 'John Doe',
      source: 'email',
      processingStatus: 'completed',
      isTemplateMatch: false,
      receivedAt: new Date().toISOString(),
      analysis: {
        id: '1',
        messageId: '1',
        sentimentScore: 0.5,
        sentimentLabel: 'positive',
        sentimentConfidence: 0.95,
        summary: 'Customer inquiry about account',
        entities: [],
        suggestedCategories: [],
        urgencyScore: 0.3,
        aiProvider: 'claude',
        aiModel: 'claude-3-sonnet',
      },
    },
    {
      id: '2',
      tenantId: '1',
      subject: 'Complaint about service',
      bodyText: 'I am very unhappy...',
      senderEmail: 'jane@example.com',
      senderName: 'Jane Smith',
      source: 'form',
      processingStatus: 'completed',
      isTemplateMatch: false,
      receivedAt: new Date(Date.now() - 3600000).toISOString(),
      analysis: {
        id: '2',
        messageId: '2',
        sentimentScore: -0.7,
        sentimentLabel: 'negative',
        sentimentConfidence: 0.92,
        summary: 'Customer complaint',
        entities: [],
        suggestedCategories: [],
        urgencyScore: 0.8,
        aiProvider: 'claude',
        aiModel: 'claude-3-sonnet',
      },
    },
    {
      id: '3',
      tenantId: '1',
      subject: 'Support Bill XYZ',
      bodyText: 'As your constituent, I urge you...',
      senderEmail: 'activist@example.com',
      senderName: 'Campaign Sender',
      source: 'email',
      processingStatus: 'completed',
      isTemplateMatch: true,
      templateSimilarityScore: 0.95,
      receivedAt: new Date(Date.now() - 7200000).toISOString(),
      analysis: {
        id: '3',
        messageId: '3',
        sentimentScore: 0.1,
        sentimentLabel: 'neutral',
        sentimentConfidence: 0.88,
        summary: 'Campaign email about legislation',
        entities: [],
        suggestedCategories: [],
        urgencyScore: 0.4,
        aiProvider: 'claude',
        aiModel: 'claude-3-sonnet',
      },
    },
  ];

  const displayData = data?.items || mockData;
  const total = data?.total || mockData.length;

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>Messages</h2>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={8} lg={6}>
            <Input
              placeholder="Search messages..."
              prefix={<SearchOutlined />}
              value={messageFilters.search}
              onChange={(e) =>
                setMessageFilters({ ...messageFilters, search: e.target.value })
              }
              allowClear
            />
          </Col>

          <Col xs={24} sm={12} md={8} lg={4}>
            <Select
              placeholder="Source"
              style={{ width: '100%' }}
              value={messageFilters.source}
              onChange={(value) =>
                setMessageFilters({ ...messageFilters, source: value })
              }
              allowClear
              options={[
                { value: 'email', label: 'Email' },
                { value: 'form', label: 'Form' },
                { value: 'api', label: 'API' },
                { value: 'upload', label: 'Upload' },
              ]}
            />
          </Col>

          <Col xs={24} sm={12} md={8} lg={4}>
            <Select
              placeholder="Sentiment"
              style={{ width: '100%' }}
              value={messageFilters.sentiment}
              onChange={(value) =>
                setMessageFilters({ ...messageFilters, sentiment: value })
              }
              allowClear
              options={[
                { value: 'positive', label: 'Positive' },
                { value: 'neutral', label: 'Neutral' },
                { value: 'negative', label: 'Negative' },
              ]}
            />
          </Col>

          <Col xs={24} sm={12} md={12} lg={6}>
            <RangePicker
              style={{ width: '100%' }}
              onChange={(dates) => {
                if (dates && dates[0] && dates[1]) {
                  setMessageFilters({
                    ...messageFilters,
                    dateRange: [
                      dates[0].toISOString(),
                      dates[1].toISOString(),
                    ],
                  });
                } else {
                  setMessageFilters({
                    ...messageFilters,
                    dateRange: undefined,
                  });
                }
              }}
            />
          </Col>

          <Col>
            <Space>
              <Button
                icon={<FilterOutlined />}
                onClick={() => setMessageFilters({})}
              >
                Clear
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => refetch()}
              >
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Table
        columns={columns}
        dataSource={displayData}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} messages`,
          onChange: (page, pageSize) => {
            setPage(page);
            setPageSize(pageSize);
          },
        }}
        rowSelection={{
          type: 'checkbox',
          onChange: (selectedRowKeys) => {
            console.log('Selected:', selectedRowKeys);
          },
        }}
      />
    </div>
  );
}
