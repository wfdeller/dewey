/**
 * Role create/edit modal
 */

import { useEffect, useMemo } from 'react';
import {
  Modal,
  Form,
  Input,
  Checkbox,
  Collapse,
  Space,
  Alert,
  message,
  Spin,
  Typography,
} from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  rolesService,
  Role,
  RoleCreateRequest,
  RoleUpdateRequest,
  PermissionInfo,
} from '../../services/usersService';
import { getErrorMessage } from '../../services/api';

const { Text } = Typography;
const { TextArea } = Input;

interface RoleModalProps {
  role: Role | null;
  isCreating: boolean;
  open: boolean;
  onClose: () => void;
}

export default function RoleModal({ role, isCreating, open, onClose }: RoleModalProps) {
  const queryClient = useQueryClient();
  const [form] = Form.useForm();

  // Fetch available permissions
  const { data: permissionsData, isLoading: permissionsLoading } = useQuery({
    queryKey: ['permissions'],
    queryFn: () => rolesService.listPermissions(),
    enabled: open,
  });

  // Group permissions by category
  const permissionsByCategory = useMemo(() => {
    if (!permissionsData?.permissions) return {};

    return permissionsData.permissions.reduce(
      (acc: Record<string, PermissionInfo[]>, perm: PermissionInfo) => {
        if (!acc[perm.category]) {
          acc[perm.category] = [];
        }
        acc[perm.category].push(perm);
        return acc;
      },
      {}
    );
  }, [permissionsData]);

  // Create role mutation
  const createMutation = useMutation({
    mutationFn: (data: RoleCreateRequest) => rolesService.createRole(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      message.success('Role created successfully');
      onClose();
    },
    onError: (error) => {
      message.error(getErrorMessage(error));
    },
  });

  // Update role mutation
  const updateMutation = useMutation({
    mutationFn: (data: RoleUpdateRequest) => rolesService.updateRole(role!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      message.success('Role updated successfully');
      onClose();
    },
    onError: (error) => {
      message.error(getErrorMessage(error));
    },
  });

  // Populate form when role data loads
  useEffect(() => {
    if (open && role && !isCreating) {
      form.setFieldsValue({
        name: role.name,
        description: role.description || '',
        permissions: role.permissions,
        azure_ad_group_id: role.azure_ad_group_id || '',
      });
    } else if (open && isCreating) {
      form.resetFields();
    }
  }, [role, isCreating, open, form]);

  // Reset form when modal closes
  useEffect(() => {
    if (!open) {
      form.resetFields();
    }
  }, [open, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      const data = {
        name: values.name,
        description: values.description || undefined,
        permissions: values.permissions || [],
        azure_ad_group_id: values.azure_ad_group_id || undefined,
      };

      if (isCreating) {
        await createMutation.mutateAsync(data);
      } else {
        await updateMutation.mutateAsync(data);
      }
    } catch {
      // Form validation error - handled by antd
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const isSystemRole = role?.is_system || false;

  const renderPermissionsSelector = () => {
    if (permissionsLoading) {
      return (
        <div style={{ textAlign: 'center', padding: 20 }}>
          <Spin />
        </div>
      );
    }

    const categories = Object.keys(permissionsByCategory).sort();

    return (
      <Collapse
        items={categories.map((category) => ({
          key: category,
          label: (
            <Space>
              <strong>{category}</strong>
              <Text type="secondary">
                ({permissionsByCategory[category].length} permissions)
              </Text>
            </Space>
          ),
          children: (
            <Form.Item
              name="permissions"
              noStyle
              valuePropName="value"
              getValueFromEvent={(checkedValues) => checkedValues}
            >
              <Checkbox.Group style={{ width: '100%' }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {permissionsByCategory[category].map((perm: PermissionInfo) => (
                    <Checkbox key={perm.key} value={perm.key}>
                      <Space direction="vertical" size={0}>
                        <span>{perm.name}</span>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {perm.description}
                        </Text>
                      </Space>
                    </Checkbox>
                  ))}
                </Space>
              </Checkbox.Group>
            </Form.Item>
          ),
        }))}
        defaultActiveKey={categories}
      />
    );
  };

  return (
    <Modal
      title={isCreating ? 'Create Role' : `Edit Role: ${role?.name}`}
      open={open}
      onCancel={onClose}
      onOk={handleSave}
      okText={isCreating ? 'Create' : 'Save Changes'}
      confirmLoading={isSaving}
      width={700}
    >
      <Form form={form} layout="vertical">
        {isSystemRole && (
          <Alert
            message="System Role"
            description="System role names cannot be changed, but you can customize the permissions."
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Form.Item
          name="name"
          label="Role Name"
          rules={[
            { required: true, message: 'Role name is required' },
            { max: 50, message: 'Role name must be 50 characters or less' },
          ]}
        >
          <Input placeholder="e.g., Support Agent" disabled={isSystemRole} />
        </Form.Item>

        <Form.Item
          name="description"
          label="Description"
          rules={[{ max: 255, message: 'Description must be 255 characters or less' }]}
        >
          <TextArea
            placeholder="Describe what this role is for..."
            rows={2}
            showCount
            maxLength={255}
          />
        </Form.Item>

        <Form.Item
          name="azure_ad_group_id"
          label="Azure AD Group ID (Optional)"
          extra="If set, users in this Azure AD group will automatically be assigned this role."
        >
          <Input placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
        </Form.Item>

        <Form.Item label="Permissions" required>
          {renderPermissionsSelector()}
        </Form.Item>
      </Form>
    </Modal>
  );
}
