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
    EyeOutlined,
    MoreOutlined,
    FormOutlined,
    FileTextOutlined,
    BarChartOutlined,
    CodeOutlined,
    LinkOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Form as FormType, FormStatus } from '../types';
import {
    useFormsQuery,
    useCreateFormMutation,
    useUpdateFormMutation,
    useDeleteFormMutation,
    useDuplicateFormMutation,
} from '../services/formsService';
import { getErrorMessage } from '../services/api';

const { Title, Text } = Typography;

interface FormModalState {
    visible: boolean;
    mode: 'create' | 'edit';
    form?: FormType;
}

interface DuplicateModalState {
    visible: boolean;
    form?: FormType;
}

export default function Forms() {
    const navigate = useNavigate();
    const [statusFilter, setStatusFilter] = useState<FormStatus | undefined>();
    const [formModal, setFormModal] = useState<FormModalState>({ visible: false, mode: 'create' });
    const [duplicateModal, setDuplicateModal] = useState<DuplicateModalState>({ visible: false });
    const [form] = Form.useForm();
    const [duplicateForm] = Form.useForm();

    const { data, isLoading, refetch } = useFormsQuery(statusFilter);
    const createMutation = useCreateFormMutation();
    const updateMutation = useUpdateFormMutation();
    const deleteMutation = useDeleteFormMutation();
    const duplicateMutation = useDuplicateFormMutation();

    const handleCreate = () => {
        form.resetFields();
        setFormModal({ visible: true, mode: 'create' });
    };

    const handleEdit = (record: FormType) => {
        form.setFieldsValue({
            name: record.name,
            description: record.description,
            slug: record.slug,
            status: record.status,
        });
        setFormModal({ visible: true, mode: 'edit', form: record });
    };

    const handleDuplicate = (record: FormType) => {
        duplicateForm.setFieldsValue({
            name: `${record.name} (Copy)`,
            slug: `${record.slug}-copy`,
        });
        setDuplicateModal({ visible: true, form: record });
    };

    const handleSubmit = async () => {
        // Prevent double submission
        if (createMutation.isPending || updateMutation.isPending) {
            return;
        }
        try {
            const values = await form.validateFields();
            if (formModal.mode === 'create') {
                await createMutation.mutateAsync(values);
                message.success('Form created successfully');
            } else if (formModal.form) {
                await updateMutation.mutateAsync({
                    formId: formModal.form.id,
                    data: values,
                });
                message.success('Form updated successfully');
            }
            setFormModal({ visible: false, mode: 'create' });
            form.resetFields();
            refetch();
        } catch (error) {
            // Only show error if it's not a validation error
            if (error && typeof error === 'object' && 'errorFields' in error) {
                return; // Form validation error, Ant Design handles this
            }
            message.error(getErrorMessage(error));
        }
    };

    const handleDuplicateSubmit = async () => {
        try {
            const values = await duplicateForm.validateFields();
            if (duplicateModal.form) {
                await duplicateMutation.mutateAsync({
                    formId: duplicateModal.form.id,
                    newName: values.name,
                    newSlug: values.slug,
                });
                message.success('Form duplicated successfully');
                setDuplicateModal({ visible: false });
                refetch();
            }
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleDelete = async (formId: string) => {
        try {
            await deleteMutation.mutateAsync(formId);
            message.success('Form deleted successfully');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const getStatusColor = (status: FormStatus) => {
        switch (status) {
            case 'published':
                return 'green';
            case 'draft':
                return 'orange';
            case 'archived':
                return 'default';
            default:
                return 'default';
        }
    };

    const columns: ColumnsType<FormType> = [
        {
            title: 'Name',
            dataIndex: 'name',
            key: 'name',
            render: (name: string, record) => (
                <Space direction='vertical' size={0}>
                    <Text strong>{name}</Text>
                    {record.description && (
                        <Text type='secondary' style={{ fontSize: 12 }}>
                            {record.description}
                        </Text>
                    )}
                </Space>
            ),
        },
        {
            title: 'Slug',
            dataIndex: 'slug',
            key: 'slug',
            render: (slug: string) => <Text code>{slug}</Text>,
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: (status: FormStatus) => <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>,
        },
        {
            title: 'Actions',
            key: 'actions',
            width: 150,
            render: (_, record) => (
                <Space size='small'>
                    <Button
                        type='primary'
                        size='small'
                        icon={<EditOutlined />}
                        onClick={() => navigate(`/forms/${record.id}/builder`)}
                    >
                        Edit
                    </Button>
                    <Dropdown
                        menu={{
                            items: [
                                {
                                    key: 'preview',
                                    icon: <EyeOutlined />,
                                    label: 'Preview',
                                    onClick: () => navigate(`/forms/${record.id}/preview`),
                                },
                                {
                                    key: 'submissions',
                                    icon: <FileTextOutlined />,
                                    label: 'Submissions',
                                    onClick: () => navigate(`/forms/${record.id}/submissions`),
                                },
                                {
                                    key: 'analytics',
                                    icon: <BarChartOutlined />,
                                    label: 'Analytics',
                                    onClick: () => navigate(`/forms/${record.id}/analytics`),
                                },
                                {
                                    key: 'embed',
                                    icon: <CodeOutlined />,
                                    label: 'Embed Code',
                                    onClick: () => navigate(`/forms/${record.id}/embed`),
                                },
                                {
                                    key: 'links',
                                    icon: <LinkOutlined />,
                                    label: 'Manage Links',
                                    onClick: () => navigate(`/forms/${record.id}/links`),
                                },
                                { type: 'divider' },
                                {
                                    key: 'settings',
                                    icon: <FormOutlined />,
                                    label: 'Settings',
                                    onClick: () => handleEdit(record),
                                },
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
                                            title: 'Delete Form',
                                            content: `Are you sure you want to delete "${record.name}"? This will also delete all submissions.`,
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
                        <Button size='small' icon={<MoreOutlined />} />
                    </Dropdown>
                </Space>
            ),
        },
    ];

    // Calculate stats
    const stats = {
        total: data?.total || 0,
        published: data?.items.filter((f) => f.status === 'published').length || 0,
        draft: data?.items.filter((f) => f.status === 'draft').length || 0,
    };

    return (
        <div>
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={2} style={{ margin: 0 }}>
                    Forms
                </Title>
                <Button type='primary' icon={<PlusOutlined />} onClick={handleCreate}>
                    Create Form
                </Button>
            </div>

            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={8}>
                    <Card>
                        <Statistic title='Total Forms' value={stats.total} prefix={<FormOutlined />} />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card>
                        <Statistic title='Published' value={stats.published} valueStyle={{ color: '#52c41a' }} />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card>
                        <Statistic title='Drafts' value={stats.draft} valueStyle={{ color: '#faad14' }} />
                    </Card>
                </Col>
            </Row>

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
                                { value: 'draft', label: 'Draft' },
                                { value: 'published', label: 'Published' },
                                { value: 'archived', label: 'Archived' },
                            ]}
                        />
                    </Space>
                </div>

                <Table
                    columns={columns}
                    dataSource={data?.items}
                    rowKey='id'
                    loading={isLoading}
                    pagination={{
                        total: data?.total,
                        showSizeChanger: true,
                        showTotal: (total) => `${total} forms`,
                    }}
                />
            </Card>

            {/* Create/Edit Form Modal */}
            <Modal
                title={formModal.mode === 'create' ? 'Create Form' : 'Edit Form Settings'}
                open={formModal.visible}
                onOk={handleSubmit}
                onCancel={() => setFormModal({ visible: false, mode: 'create' })}
                confirmLoading={createMutation.isPending || updateMutation.isPending}
            >
                <Form form={form} layout='vertical'>
                    <Form.Item
                        name='name'
                        label='Form Name'
                        rules={[{ required: true, message: 'Please enter a form name' }]}
                    >
                        <Input placeholder='e.g., Contact Form, Feedback Survey' />
                    </Form.Item>

                    <Form.Item name='description' label='Description'>
                        <Input.TextArea rows={3} placeholder='Brief description of this form' />
                    </Form.Item>

                    <Form.Item
                        name='slug'
                        label='URL Slug'
                        rules={[
                            { required: true, message: 'Please enter a URL slug' },
                            {
                                pattern: /^[a-z0-9-]+$/,
                                message: 'Slug can only contain lowercase letters, numbers, and hyphens',
                            },
                        ]}
                        extra='Used in the form URL: /f/your-tenant/this-slug'
                    >
                        <Input placeholder='e.g., contact-form' />
                    </Form.Item>

                    {formModal.mode === 'edit' && (
                        <Form.Item name='status' label='Status'>
                            <Select
                                options={[
                                    { value: 'draft', label: 'Draft' },
                                    { value: 'published', label: 'Published' },
                                    { value: 'archived', label: 'Archived' },
                                ]}
                            />
                        </Form.Item>
                    )}
                </Form>
            </Modal>

            {/* Duplicate Form Modal */}
            <Modal
                title='Duplicate Form'
                open={duplicateModal.visible}
                onOk={handleDuplicateSubmit}
                onCancel={() => setDuplicateModal({ visible: false })}
                confirmLoading={duplicateMutation.isPending}
            >
                <Form form={duplicateForm} layout='vertical'>
                    <Form.Item
                        name='name'
                        label='New Form Name'
                        rules={[{ required: true, message: 'Please enter a name' }]}
                    >
                        <Input />
                    </Form.Item>

                    <Form.Item
                        name='slug'
                        label='New URL Slug'
                        rules={[
                            { required: true, message: 'Please enter a slug' },
                            {
                                pattern: /^[a-z0-9-]+$/,
                                message: 'Slug can only contain lowercase letters, numbers, and hyphens',
                            },
                        ]}
                    >
                        <Input />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
