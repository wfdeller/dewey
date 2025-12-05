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
  message,
  Dropdown,
  Card,
  Row,
  Col,
  Statistic,
  Select,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  MoreOutlined,
  MailOutlined,
  SendOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  EmailTemplate,
  useEmailTemplatesQuery,
  useCreateEmailTemplateMutation,
  useDeleteEmailTemplateMutation,
  useDuplicateEmailTemplateMutation,
} from '../services/emailService';
import { getErrorMessage } from '../services/api';

const { Title, Text } = Typography;

interface CreateModalState {
  visible: boolean;
}

interface DuplicateModalState {
  visible: boolean;
  template?: EmailTemplate;
}

export default function EmailTemplates() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<boolean | undefined>();
  const [createModal, setCreateModal] = useState<CreateModalState>({ visible: false });
  const [duplicateModal, setDuplicateModal] = useState<DuplicateModalState>({ visible: false });
  const [form] = Form.useForm();
  const [duplicateForm] = Form.useForm();

  const { data, isLoading, refetch } = useEmailTemplatesQuery(statusFilter);
  const createMutation = useCreateEmailTemplateMutation();
  const deleteMutation = useDeleteEmailTemplateMutation();
  const duplicateMutation = useDuplicateEmailTemplateMutation();

  const handleCreate = () => {
    form.resetFields();
    setCreateModal({ visible: true });
  };

  const handleDuplicate = (record: EmailTemplate) => {
    duplicateForm.setFieldsValue({
      name: `${record.name} (Copy)`,
    });
    setDuplicateModal({ visible: true, template: record });
  };

  const handleSubmit = async () => {
    if (createMutation.isPending) return;

    try {
      const values = await form.validateFields();
      const template = await createMutation.mutateAsync({
        name: values.name,
        description: values.description,
        subject: 'New Email Template',
        body_html: '<p>Enter your email content here...</p>',
      });
      message.success('Template created successfully');
      setCreateModal({ visible: false });
      form.resetFields();
      navigate(`/email-templates/${template.id}/editor`);
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return;
      }
      message.error(getErrorMessage(error));
    }
  };

  const handleDuplicateSubmit = async () => {
    try {
      const values = await duplicateForm.validateFields();
      if (duplicateModal.template) {
        await duplicateMutation.mutateAsync({
          templateId: duplicateModal.template.id,
          new_name: values.name,
        });
        message.success('Template duplicated successfully');
        setDuplicateModal({ visible: false });
        refetch();
      }
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  const handleDelete = async (templateId: string) => {
    try {
      await deleteMutation.mutateAsync(templateId);
      message.success('Template deleted successfully');
      refetch();
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  const columns: ColumnsType<EmailTemplate> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          {record.description && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.description}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Subject',
      dataIndex: 'subject',
      key: 'subject',
      render: (subject: string) => (
        <Text ellipsis style={{ maxWidth: 250 }}>{subject}</Text>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'isActive',
      key: 'isActive',
      width: 100,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'default'}>
          {isActive ? 'ACTIVE' : 'INACTIVE'}
        </Tag>
      ),
    },
    {
      title: 'Sends',
      dataIndex: 'sendCount',
      key: 'sendCount',
      width: 80,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: 'Last Sent',
      dataIndex: 'lastSentAt',
      key: 'lastSentAt',
      width: 150,
      render: (date: string | undefined) =>
        date ? new Date(date).toLocaleDateString() : 'Never',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="primary"
            size="small"
            icon={<EditOutlined />}
            onClick={() => navigate(`/email-templates/${record.id}/editor`)}
          >
            Edit
          </Button>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'duplicate',
                  icon: <CopyOutlined />,
                  label: 'Duplicate',
                  onClick: () => handleDuplicate(record),
                },
                { type: 'divider' },
                {
                  key: 'delete',
                  icon: <DeleteOutlined />,
                  label: 'Delete',
                  danger: true,
                  onClick: () => {
                    Modal.confirm({
                      title: 'Delete Template',
                      content: `Are you sure you want to delete "${record.name}"?`,
                      okText: 'Delete',
                      okType: 'danger',
                      onOk: () => handleDelete(record.id),
                    });
                  },
                },
              ],
            }}
            trigger={['click']}
          >
            <Button size="small" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  // Calculate stats
  const stats = {
    total: data?.total || 0,
    active: data?.items.filter((t) => t.is_active).length || 0,
    totalSends: data?.items.reduce((sum, t) => sum + t.send_count, 0) || 0,
  };

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2} style={{ margin: 0 }}>Email Templates</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          Create Template
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic title="Total Templates" value={stats.total} prefix={<MailOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Active"
              value={stats.active}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Sends"
              value={stats.totalSends}
              prefix={<SendOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Text>Status:</Text>
            <Select
              style={{ width: 150 }}
              placeholder="All statuses"
              allowClear
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: true, label: 'Active' },
                { value: false, label: 'Inactive' },
              ]}
            />
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={data?.items}
          rowKey="id"
          loading={isLoading}
          pagination={{
            total: data?.total,
            showSizeChanger: true,
            showTotal: (total) => `${total} templates`,
          }}
        />
      </Card>

      {/* Create Template Modal */}
      <Modal
        title="Create Email Template"
        open={createModal.visible}
        onOk={handleSubmit}
        onCancel={() => setCreateModal({ visible: false })}
        confirmLoading={createMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Template Name"
            rules={[{ required: true, message: 'Please enter a template name' }]}
          >
            <Input placeholder="e.g., Welcome Email, Follow-up Response" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="Brief description of this template" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Duplicate Template Modal */}
      <Modal
        title="Duplicate Template"
        open={duplicateModal.visible}
        onOk={handleDuplicateSubmit}
        onCancel={() => setDuplicateModal({ visible: false })}
        confirmLoading={duplicateMutation.isPending}
      >
        <Form form={duplicateForm} layout="vertical">
          <Form.Item
            name="name"
            label="New Template Name"
            rules={[{ required: true, message: 'Please enter a name' }]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
