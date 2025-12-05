/**
 * Users management tab for Settings page
 */

import { useState } from 'react';
import { Table, Button, Input, Space, Tag, Switch, message, Popconfirm, Typography } from 'antd';
import {
    SearchOutlined,
    UserOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    WindowsOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import { usersService, UserListItem } from '../../services/usersService';
import { getErrorMessage } from '../../services/api';
import UserDetailModal from './UserDetailModal';

const { Text } = Typography;

export default function UsersTab() {
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [selectedUser, setSelectedUser] = useState<UserListItem | null>(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);

    // Fetch users
    const { data, isLoading } = useQuery({
        queryKey: ['users', { page, pageSize, search }],
        queryFn: () =>
            usersService.listUsers({
                page,
                page_size: pageSize,
                search: search || undefined,
            }),
    });

    // Update user mutation (for quick toggle)
    const updateUserMutation = useMutation({
        mutationFn: ({ userId, data }: { userId: string; data: { is_active: boolean } }) =>
            usersService.updateUser(userId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            message.success('User updated successfully');
        },
        onError: (error) => {
            message.error(getErrorMessage(error));
        },
    });

    const handleToggleActive = (user: UserListItem) => {
        updateUserMutation.mutate({
            userId: user.id,
            data: { is_active: !user.is_active },
        });
    };

    const handleViewUser = (user: UserListItem) => {
        setSelectedUser(user);
        setDetailModalOpen(true);
    };

    const columns: ColumnsType<UserListItem> = [
        {
            title: 'User',
            key: 'user',
            render: (_, record) => (
                <Space>
                    <UserOutlined />
                    <div>
                        <div>{record.name}</div>
                        <Text type='secondary' style={{ fontSize: 12 }}>
                            {record.email}
                        </Text>
                    </div>
                </Space>
            ),
        },
        {
            title: 'Roles',
            key: 'roles',
            dataIndex: 'roles',
            render: (roles: string[]) => (
                <Space wrap>
                    {roles.map((role) => (
                        <Tag key={role} color={role === 'owner' ? 'gold' : role === 'admin' ? 'blue' : 'default'}>
                            {role}
                        </Tag>
                    ))}
                </Space>
            ),
        },
        {
            title: 'SSO',
            key: 'sso',
            width: 80,
            align: 'center',
            render: (_, record) =>
                record.azure_ad_oid ? (
                    <Tag icon={<WindowsOutlined />} color='blue'>
                        Azure AD
                    </Tag>
                ) : (
                    <Text type='secondary'>-</Text>
                ),
        },
        {
            title: 'Status',
            key: 'status',
            width: 100,
            render: (_, record) =>
                record.is_active ? (
                    <Tag icon={<CheckCircleOutlined />} color='success'>
                        Active
                    </Tag>
                ) : (
                    <Tag icon={<CloseCircleOutlined />} color='error'>
                        Inactive
                    </Tag>
                ),
        },
        {
            title: 'Created',
            key: 'created_at',
            dataIndex: 'created_at',
            width: 120,
            render: (date: string) => new Date(date).toLocaleDateString(),
        },
        {
            title: 'Actions',
            key: 'actions',
            width: 180,
            render: (_, record) => (
                <Space>
                    <Button size='small' onClick={() => handleViewUser(record)}>
                        Edit
                    </Button>
                    <Popconfirm
                        title={record.is_active ? 'Deactivate user?' : 'Activate user?'}
                        description={
                            record.is_active
                                ? 'This will prevent the user from logging in.'
                                : 'This will allow the user to log in again.'
                        }
                        onConfirm={() => handleToggleActive(record)}
                        okText='Yes'
                        cancelText='No'
                    >
                        <Switch size='small' checked={record.is_active} loading={updateUserMutation.isPending} />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                <Input
                    placeholder='Search users...'
                    prefix={<SearchOutlined />}
                    value={search}
                    onChange={(e) => {
                        setSearch(e.target.value);
                        setPage(1);
                    }}
                    style={{ width: 300 }}
                    allowClear
                />
            </div>

            <Table
                columns={columns}
                dataSource={data?.users || []}
                rowKey='id'
                loading={isLoading}
                pagination={{
                    current: page,
                    pageSize: pageSize,
                    total: data?.total || 0,
                    showSizeChanger: true,
                    showTotal: (total) => `${total} users`,
                    onChange: (p, ps) => {
                        setPage(p);
                        setPageSize(ps);
                    },
                }}
            />

            <UserDetailModal
                userId={selectedUser?.id || null}
                open={detailModalOpen}
                onClose={() => {
                    setDetailModalOpen(false);
                    setSelectedUser(null);
                }}
            />
        </div>
    );
}
