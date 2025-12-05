import { useState } from 'react';
import {
    Table,
    Button,
    Space,
    Modal,
    Form,
    Input,
    Switch,
    Tabs,
    Typography,
    Popconfirm,
    Tag,
    Spin,
    Alert,
    App,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
    useLOVQuery,
    useLOVTypesQuery,
    useCreateLOVMutation,
    useUpdateLOVMutation,
    useDeleteLOVMutation,
    useSeedLOVMutation,
    LOVItem,
} from '../../services/lovService';
import { getErrorMessage } from '../../services/api';

const { Title, Text } = Typography;

export default function LOVTab() {
    const { message } = App.useApp();
    const [selectedListType, setSelectedListType] = useState('prefix');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingItem, setEditingItem] = useState<LOVItem | null>(null);
    const [form] = Form.useForm();

    const { data: lovData, isLoading } = useLOVQuery();
    const { data: typesData } = useLOVTypesQuery();
    const createMutation = useCreateLOVMutation();
    const updateMutation = useUpdateLOVMutation();
    const deleteMutation = useDeleteLOVMutation();
    const seedMutation = useSeedLOVMutation();

    const currentItems = lovData?.[selectedListType as keyof typeof lovData] || [];

    const handleOpenModal = (item?: LOVItem) => {
        if (item) {
            setEditingItem(item);
            form.setFieldsValue({
                value: item.value,
                label: item.label,
                is_active: item.is_active,
            });
        } else {
            setEditingItem(null);
            form.resetFields();
            form.setFieldsValue({ is_active: true });
        }
        setIsModalOpen(true);
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();

            if (editingItem) {
                await updateMutation.mutateAsync({
                    entryId: editingItem.id,
                    data: {
                        value: values.value,
                        label: values.label,
                        is_active: values.is_active,
                    },
                });
                message.success('Entry updated successfully');
            } else {
                await createMutation.mutateAsync({
                    listType: selectedListType,
                    data: {
                        value: values.value || values.label.toLowerCase().replace(/[^a-z0-9]+/g, '_'),
                        label: values.label,
                        is_active: values.is_active,
                    },
                });
                message.success('Entry created successfully');
            }

            setIsModalOpen(false);
            form.resetFields();
            setEditingItem(null);
        } catch (error) {
            if (error && typeof error === 'object' && 'errorFields' in error) {
                return;
            }
            message.error(getErrorMessage(error));
        }
    };

    const handleDelete = async (item: LOVItem) => {
        try {
            await deleteMutation.mutateAsync(item.id);
            message.success('Entry deleted successfully');
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleSeedDefaults = async () => {
        try {
            const result = await seedMutation.mutateAsync();
            if (result.seeded_count > 0) {
                message.success(`Seeded ${result.seeded_count} default entries for: ${result.list_types.join(', ')}`);
            } else {
                message.info('All list types already have data');
            }
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const columns: ColumnsType<LOVItem> = [
        {
            title: 'Label',
            dataIndex: 'label',
            key: 'label',
        },
        {
            title: 'Value',
            dataIndex: 'value',
            key: 'value',
            render: (value: string) => <Text code>{value}</Text>,
        },
        {
            title: 'Order',
            dataIndex: 'sort_order',
            key: 'sort_order',
            width: 80,
            align: 'center',
        },
        {
            title: 'Status',
            dataIndex: 'is_active',
            key: 'is_active',
            width: 100,
            render: (isActive: boolean) => (
                <Tag color={isActive ? 'green' : 'default'}>{isActive ? 'Active' : 'Inactive'}</Tag>
            ),
        },
        {
            title: 'Actions',
            key: 'actions',
            width: 120,
            render: (_, record) => (
                <Space size='small'>
                    <Button type='text' size='small' icon={<EditOutlined />} onClick={() => handleOpenModal(record)} />
                    <Popconfirm
                        title='Delete this entry?'
                        description='Consider deactivating instead to preserve historical data.'
                        onConfirm={() => handleDelete(record)}
                        okText='Delete'
                        okType='danger'
                    >
                        <Button type='text' size='small' danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    const listTypeTabs =
        typesData?.types.map((type) => ({
            key: type.key,
            label: type.name,
            children: null,
        })) || [];

    if (isLoading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
                <Spin size='large' />
            </div>
        );
    }

    // Check if LOV data is empty (needs seeding)
    const needsSeeding = lovData && Object.values(lovData).every((arr) => arr.length === 0);

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                    <Title level={5} style={{ margin: 0 }}>
                        List of Values
                    </Title>
                    <Text type='secondary'>Manage dropdown options used throughout the application</Text>
                </div>
                <Space>
                    <Button icon={<ReloadOutlined />} onClick={handleSeedDefaults} loading={seedMutation.isPending}>
                        Seed Defaults
                    </Button>
                    <Button type='primary' icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
                        Add Entry
                    </Button>
                </Space>
            </div>

            {needsSeeding && (
                <Alert
                    message='No list values found'
                    description="Click 'Seed Defaults' to populate the lists with default values, or add entries manually."
                    type='info'
                    showIcon
                    style={{ marginBottom: 16 }}
                />
            )}

            <Tabs
                activeKey={selectedListType}
                onChange={setSelectedListType}
                items={
                    listTypeTabs.length > 0
                        ? listTypeTabs
                        : [
                              { key: 'prefix', label: 'Prefixes' },
                              { key: 'pronoun', label: 'Pronouns' },
                              { key: 'language', label: 'Languages' },
                              { key: 'gender', label: 'Genders' },
                              { key: 'marital_status', label: 'Marital Status' },
                              { key: 'education_level', label: 'Education' },
                              { key: 'income_bracket', label: 'Income Brackets' },
                              { key: 'homeowner_status', label: 'Homeowner' },
                              { key: 'voter_status', label: 'Voter Status' },
                              { key: 'communication_pref', label: 'Communication' },
                              { key: 'inactive_reason', label: 'Inactive Reasons' },
                          ]
                }
                style={{ marginBottom: 16 }}
            />

            <Table
                columns={columns}
                dataSource={currentItems}
                rowKey='id'
                pagination={false}
                size='small'
                locale={{
                    emptyText: (
                        <div style={{ padding: 24 }}>
                            <Text type='secondary'>No entries for this list type.</Text>
                            <br />
                            <Button type='link' onClick={() => handleOpenModal()} style={{ padding: 0 }}>
                                Add the first entry
                            </Button>
                        </div>
                    ),
                }}
            />

            <Modal
                title={editingItem ? 'Edit Entry' : 'Add Entry'}
                open={isModalOpen}
                onOk={handleSubmit}
                onCancel={() => {
                    setIsModalOpen(false);
                    setEditingItem(null);
                    form.resetFields();
                }}
                confirmLoading={createMutation.isPending || updateMutation.isPending}
            >
                <Form form={form} layout='vertical'>
                    <Form.Item
                        name='label'
                        label='Display Label'
                        rules={[{ required: true, message: 'Please enter a display label' }]}
                    >
                        <Input placeholder="e.g., Mr., Bachelor's Degree, English" />
                    </Form.Item>
                    <Form.Item
                        name='value'
                        label='Value'
                        help='Stored in database. Auto-generated from label if left blank.'
                    >
                        <Input placeholder='e.g., mr, bachelors, en' />
                    </Form.Item>
                    <Form.Item name='is_active' label='Active' valuePropName='checked'>
                        <Switch checkedChildren='Yes' unCheckedChildren='No' />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
