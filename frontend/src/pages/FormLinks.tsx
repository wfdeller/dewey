import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Switch,
  DatePicker,
  message,
  Card,
  Row,
  Col,
  Statistic,
  Tooltip,
  Popconfirm,
  Empty,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  CopyOutlined,
  LinkOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  useFormQuery,
  useFormLinksQuery,
  useCreateFormLinkMutation,
  useRevokeFormLinkMutation,
  FormLink,
} from '../services/formsService';
import { getErrorMessage } from '../services/api';

const { Title, Text, Paragraph } = Typography;

export default function FormLinks() {
  const { formId } = useParams<{ formId: string }>();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [form] = Form.useForm();

  const { data: formData } = useFormQuery(formId || '');
  const { data: linksData, isLoading, refetch } = useFormLinksQuery(formId || '', page, pageSize);
  const createMutation = useCreateFormLinkMutation();
  const revokeMutation = useRevokeFormLinkMutation();

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await createMutation.mutateAsync({
        formId: formId!,
        data: {
          contact_id: values.contactId,
          is_single_use: values.is_single_use || false,
          expires_at: values.expires_at ? values.expires_at.toISOString() : undefined,
        },
      });
      message.success('Form link created successfully');
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

  const handleRevoke = async (token: string) => {
    try {
      await revokeMutation.mutateAsync({ formId: formId!, token });
      message.success('Link revoked successfully');
      refetch();
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  const copyToClipboard = async (token: string) => {
    // Construct the full URL - in production this would use the tenant slug
    const baseUrl = window.location.origin;
    const tenantSlug = 'demo'; // TODO: Get from auth context
    const formSlug = formData?.slug || '';
    const url = `${baseUrl}/f/${tenantSlug}/${formSlug}?t=${token}`;

    try {
      await navigator.clipboard.writeText(url);
      message.success('Link copied to clipboard');
    } catch {
      message.error('Failed to copy link');
    }
  };

  const getLinkStatus = (link: FormLink): { status: 'active' | 'used' | 'expired'; color: string } => {
    // Check expiration
    if (link.expires_at && new Date(link.expires_at) < new Date()) {
      return { status: 'expired', color: 'default' };
    }
    // Check single-use
    if (link.is_single_use && link.used_at) {
      return { status: 'used', color: 'orange' };
    }
    return { status: 'active', color: 'green' };
  };

  const columns: ColumnsType<FormLink> = [
    {
      title: 'Token',
      dataIndex: 'token',
      key: 'token',
      width: 200,
      render: (token: string) => (
        <Space>
          <Text code style={{ fontSize: 12 }}>{token.substring(0, 12)}...</Text>
          <Tooltip title="Copy full link">
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => copyToClipboard(token)}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Contact ID',
      dataIndex: 'contactId',
      key: 'contactId',
      render: (id: string) => (
        <Text code style={{ fontSize: 11 }}>{id.substring(0, 8)}...</Text>
      ),
    },
    {
      title: 'Type',
      key: 'type',
      width: 100,
      render: (_, record) => (
        <Tag color={record.is_single_use ? 'blue' : 'purple'}>
          {record.is_single_use ? 'Single-use' : 'Reusable'}
        </Tag>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 100,
      render: (_, record) => {
        const { status, color } = getLinkStatus(record);
        const icon = status === 'active'
          ? <CheckCircleOutlined />
          : status === 'used'
            ? <ClockCircleOutlined />
            : <CloseCircleOutlined />;
        return (
          <Tag color={color} icon={icon}>
            {status.toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: 'Uses',
      dataIndex: 'useCount',
      key: 'useCount',
      width: 80,
      align: 'center',
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 140,
      render: (date: string) => dayjs(date).format('MMM D, YYYY HH:mm'),
    },
    {
      title: 'Expires',
      dataIndex: 'expiresAt',
      key: 'expiresAt',
      width: 140,
      render: (date?: string) => date ? dayjs(date).format('MMM D, YYYY HH:mm') : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Popconfirm
          title="Revoke this link?"
          description="This action cannot be undone. The link will no longer work."
          onConfirm={() => handleRevoke(record.token)}
          okText="Revoke"
          okType="danger"
        >
          <Button danger size="small" icon={<DeleteOutlined />}>
            Revoke
          </Button>
        </Popconfirm>
      ),
    },
  ];

  // Calculate stats
  const stats = {
    total: linksData?.total || 0,
    active: linksData?.items.filter((l) => getLinkStatus(l).status === 'active').length || 0,
    used: linksData?.items.filter((l) => getLinkStatus(l).status === 'used').length || 0,
    totalUses: linksData?.items.reduce((sum, l) => sum + l.use_count, 0) || 0,
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/forms')}
          style={{ marginBottom: 8 }}
        >
          Back to Forms
        </Button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              <LinkOutlined style={{ marginRight: 8 }} />
              Form Links
            </Title>
            {formData && (
              <Text type="secondary">
                Managing links for: <Text strong>{formData.name}</Text>
              </Text>
            )}
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            Generate Link
          </Button>
        </div>
      </div>

      <Alert
        message="Pre-identified Form Links"
        description="Generate unique links for known contacts. When they submit the form via these links, their identity is automatically associated with the submission - no email required."
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="Total Links" value={stats.total} prefix={<LinkOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active"
              value={stats.active}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Used (Single-use)"
              value={stats.used}
              valueStyle={{ color: '#faad14' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Total Submissions" value={stats.totalUses} />
          </Card>
        </Col>
      </Row>

      <Card>
        {linksData?.items.length === 0 && !isLoading ? (
          <Empty
            description="No links generated yet"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button type="primary" onClick={() => setCreateModalVisible(true)}>
              Generate First Link
            </Button>
          </Empty>
        ) : (
          <Table
            columns={columns}
            dataSource={linksData?.items}
            rowKey="id"
            loading={isLoading}
            pagination={{
              current: page,
              pageSize: pageSize,
              total: linksData?.total,
              showSizeChanger: true,
              showTotal: (total) => `${total} links`,
              onChange: (p, ps) => {
                setPage(p);
                setPageSize(ps);
              },
            }}
          />
        )}
      </Card>

      {/* Create Link Modal */}
      <Modal
        title="Generate Form Link"
        open={createModalVisible}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
      >
        <Paragraph type="secondary" style={{ marginBottom: 16 }}>
          Create a unique link that pre-identifies a contact. When they submit the form
          using this link, the submission will automatically be associated with them.
        </Paragraph>

        <Form form={form} layout="vertical">
          <Form.Item
            name="contactId"
            label="Contact ID"
            rules={[
              { required: true, message: 'Please enter a contact ID' },
              {
                pattern: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
                message: 'Please enter a valid UUID',
              },
            ]}
            extra="Enter the UUID of the contact to associate with this link"
          >
            <Input placeholder="e.g., 123e4567-e89b-12d3-a456-426614174000" />
          </Form.Item>

          <Form.Item
            name="isSingleUse"
            label="Single Use"
            valuePropName="checked"
            extra="If enabled, the link becomes invalid after the first submission"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name="expiresAt"
            label="Expiration Date"
            extra="Leave empty for no expiration"
          >
            <DatePicker
              showTime
              format="YYYY-MM-DD HH:mm"
              style={{ width: '100%' }}
              disabledDate={(current) => current && current < dayjs().startOf('day')}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
