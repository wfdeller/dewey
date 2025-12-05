/**
 * User detail and edit modal
 */

import { useEffect, useState } from 'react';
import { Modal, Form, Input, Switch, Select, Descriptions, Tabs, Tag, Space, Button, message, Spin, Alert } from 'antd';
import { WindowsOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersService, rolesService, Role } from '../../services/usersService';
import { getErrorMessage } from '../../services/api';
import { useAuthStore } from '../../stores/authStore';

interface UserDetailModalProps {
    userId: string | null;
    open: boolean;
    onClose: () => void;
}

export default function UserDetailModal({ userId, open, onClose }: UserDetailModalProps) {
    const queryClient = useQueryClient();
    const [form] = Form.useForm();
    const [activeTab, setActiveTab] = useState('details');
    const currentUser = useAuthStore((state) => state.user);

    // Fetch user details
    const {
        data: user,
        isLoading: userLoading,
        error: userError,
    } = useQuery({
        queryKey: ['user', userId],
        queryFn: () => usersService.getUser(userId!),
        enabled: !!userId && open,
    });

    // Fetch available roles
    const { data: rolesData } = useQuery({
        queryKey: ['roles'],
        queryFn: () => rolesService.listRoles(),
        enabled: open,
    });

    // Update user mutation
    const updateUserMutation = useMutation({
        mutationFn: (data: { name?: string; is_active?: boolean }) => usersService.updateUser(userId!, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            queryClient.invalidateQueries({ queryKey: ['user', userId] });
            message.success('User updated successfully');
        },
        onError: (error) => {
            message.error(getErrorMessage(error));
        },
    });

    // Set user roles mutation
    const setRolesMutation = useMutation({
        mutationFn: (roleIds: string[]) => usersService.setUserRoles(userId!, roleIds),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            queryClient.invalidateQueries({ queryKey: ['user', userId] });
            message.success('Roles updated successfully');
        },
        onError: (error) => {
            message.error(getErrorMessage(error));
        },
    });

    // Populate form when user data loads
    useEffect(() => {
        if (user) {
            form.setFieldsValue({
                name: user.name,
                is_active: user.is_active,
                roles: user.roles.map((r) => r.role_id),
            });
        }
    }, [user, form]);

    // Reset form when modal closes
    useEffect(() => {
        if (!open) {
            form.resetFields();
            setActiveTab('details');
        }
    }, [open, form]);

    const handleSave = async () => {
        try {
            const values = await form.validateFields();

            // Update user info
            if (values.name !== user?.name || values.is_active !== user?.is_active) {
                await updateUserMutation.mutateAsync({
                    name: values.name,
                    is_active: values.is_active,
                });
            }

            // Update roles if changed
            const currentRoleIds = user?.roles.map((r) => r.role_id) || [];
            const newRoleIds = values.roles || [];
            const rolesChanged =
                currentRoleIds.length !== newRoleIds.length ||
                !currentRoleIds.every((id: string) => newRoleIds.includes(id));

            if (rolesChanged) {
                await setRolesMutation.mutateAsync(newRoleIds);
            }

            onClose();
        } catch {
            // Form validation error - handled by antd
        }
    };

    const isCurrentUser = currentUser?.id === userId;
    const isSaving = updateUserMutation.isPending || setRolesMutation.isPending;

    const renderDetails = () => {
        if (!user) return null;

        return (
            <Descriptions column={1} bordered size='small'>
                <Descriptions.Item label='Email'>{user.email}</Descriptions.Item>
                <Descriptions.Item label='User ID'>
                    <code style={{ fontSize: 11 }}>{user.id}</code>
                </Descriptions.Item>
                <Descriptions.Item label='Azure AD'>
                    {user.azure_ad_oid ? (
                        <Tag icon={<WindowsOutlined />} color='blue'>
                            Linked
                        </Tag>
                    ) : (
                        <Tag>Not linked</Tag>
                    )}
                </Descriptions.Item>
                <Descriptions.Item label='Created'>{new Date(user.created_at).toLocaleString()}</Descriptions.Item>
                <Descriptions.Item label='Updated'>{new Date(user.updated_at).toLocaleString()}</Descriptions.Item>
                <Descriptions.Item label='Permissions'>
                    <div style={{ maxHeight: 150, overflow: 'auto' }}>
                        <Space wrap size={[4, 4]}>
                            {user.permissions.map((perm) => (
                                <Tag key={perm} style={{ fontSize: 11 }}>
                                    {perm}
                                </Tag>
                            ))}
                        </Space>
                    </div>
                </Descriptions.Item>
            </Descriptions>
        );
    };

    const renderEditForm = () => {
        if (!user) return null;

        return (
            <Form form={form} layout='vertical'>
                {isCurrentUser && (
                    <Alert
                        message='This is your account'
                        description='Some changes may require you to log in again.'
                        type='info'
                        showIcon
                        style={{ marginBottom: 16 }}
                    />
                )}

                <Form.Item name='name' label='Name' rules={[{ required: true, message: 'Name is required' }]}>
                    <Input />
                </Form.Item>

                <Form.Item
                    name='is_active'
                    label='Active'
                    valuePropName='checked'
                    extra={isCurrentUser ? 'You cannot deactivate your own account.' : undefined}
                >
                    <Switch disabled={isCurrentUser} />
                </Form.Item>

                <Form.Item name='roles' label='Roles' extra='Select the roles to assign to this user.'>
                    <Select
                        mode='multiple'
                        placeholder='Select roles'
                        options={rolesData?.roles.map((role: Role) => ({
                            label: (
                                <Space>
                                    <span>{role.name}</span>
                                    {role.is_system && <Tag style={{ fontSize: 10 }}>System</Tag>}
                                </Space>
                            ),
                            value: role.id,
                        }))}
                    />
                </Form.Item>
            </Form>
        );
    };

    return (
        <Modal
            title={user ? `Edit User: ${user.name}` : 'User Details'}
            open={open}
            onCancel={onClose}
            width={600}
            footer={[
                <Button key='cancel' onClick={onClose}>
                    Cancel
                </Button>,
                <Button
                    key='save'
                    type='primary'
                    onClick={handleSave}
                    loading={isSaving}
                    disabled={activeTab === 'details'}
                >
                    Save Changes
                </Button>,
            ]}
        >
            {userLoading ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                    <Spin />
                </div>
            ) : userError ? (
                <Alert message='Error loading user' description={getErrorMessage(userError)} type='error' />
            ) : (
                <Tabs
                    activeKey={activeTab}
                    onChange={setActiveTab}
                    items={[
                        {
                            key: 'details',
                            label: 'Details',
                            children: renderDetails(),
                        },
                        {
                            key: 'edit',
                            label: 'Edit',
                            children: renderEditForm(),
                        },
                    ]}
                />
            )}
        </Modal>
    );
}
