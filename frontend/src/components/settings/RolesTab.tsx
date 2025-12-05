/**
 * Roles management tab for Settings page
 */

import { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Popconfirm,
  message,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UndoOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import { rolesService, Role } from '../../services/usersService';
import { getErrorMessage } from '../../services/api';
import RoleModal from './RoleModal';

const { Text } = Typography;

export default function RolesTab() {
  const queryClient = useQueryClient();
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Fetch roles
  const { data, isLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rolesService.listRoles(),
  });

  // Delete role mutation
  const deleteMutation = useMutation({
    mutationFn: (roleId: string) => rolesService.deleteRole(roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      message.success('Role deleted successfully');
    },
    onError: (error) => {
      message.error(getErrorMessage(error));
    },
  });

  // Reset role mutation
  const resetMutation = useMutation({
    mutationFn: (roleId: string) => rolesService.resetRole(roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      message.success('Role reset to defaults');
    },
    onError: (error) => {
      message.error(getErrorMessage(error));
    },
  });

  const handleCreate = () => {
    setSelectedRole(null);
    setIsCreating(true);
    setModalOpen(true);
  };

  const handleEdit = (role: Role) => {
    setSelectedRole(role);
    setIsCreating(false);
    setModalOpen(true);
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setSelectedRole(null);
    setIsCreating(false);
  };

  const columns: ColumnsType<Role> = [
    {
      title: 'Role',
      key: 'role',
      render: (_, record) => (
        <Space>
          {record.is_system && (
            <Tooltip title="System role">
              <LockOutlined style={{ color: '#1890ff' }} />
            </Tooltip>
          )}
          <div>
            <div style={{ fontWeight: 500 }}>{record.name}</div>
            {record.description && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {record.description}
              </Text>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: 'Permissions',
      key: 'permissions',
      render: (_, record) => (
        <Space wrap size={[4, 4]}>
          {record.permissions.slice(0, 5).map((perm) => (
            <Tag key={perm} style={{ fontSize: 11 }}>
              {perm.replace(/_/g, ' ')}
            </Tag>
          ))}
          {record.permissions.length > 5 && (
            <Tag style={{ fontSize: 11 }}>+{record.permissions.length - 5} more</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Azure AD Group',
      key: 'azure_ad_group_id',
      width: 150,
      render: (_, record) =>
        record.azure_ad_group_id ? (
          <Tooltip title={record.azure_ad_group_id}>
            <Tag color="blue">Synced</Tag>
          </Tooltip>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="Edit">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>

          {record.is_system ? (
            <Popconfirm
              title="Reset to defaults?"
              description="This will restore the default permissions for this system role."
              onConfirm={() => resetMutation.mutate(record.id)}
              okText="Reset"
              cancelText="Cancel"
            >
              <Tooltip title="Reset to defaults">
                <Button
                  size="small"
                  icon={<UndoOutlined />}
                  loading={resetMutation.isPending}
                />
              </Tooltip>
            </Popconfirm>
          ) : (
            <Popconfirm
              title="Delete this role?"
              description="Users with this role will lose these permissions."
              onConfirm={() => deleteMutation.mutate(record.id)}
              okText="Delete"
              okButtonProps={{ danger: true }}
              cancelText="Cancel"
            >
              <Tooltip title="Delete">
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  loading={deleteMutation.isPending}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <Text type="secondary">
            Manage roles and their permissions. System roles cannot be deleted but can be customized.
          </Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          Create Role
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data?.roles || []}
        rowKey="id"
        loading={isLoading}
        pagination={false}
      />

      <RoleModal
        role={selectedRole}
        isCreating={isCreating}
        open={modalOpen}
        onClose={handleModalClose}
      />
    </div>
  );
}
