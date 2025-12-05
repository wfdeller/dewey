/**
 * API Keys management tab for Settings page
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
  Modal,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
  CopyOutlined,
  CheckOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import { apiKeysService, APIKey } from '../../services/apiKeysService';
import { getErrorMessage } from '../../services/api';
import ApiKeyModal from './ApiKeyModal';

const { Text, Paragraph } = Typography;

export default function ApiKeysTab() {
  const queryClient = useQueryClient();
  const [selectedKey, setSelectedKey] = useState<APIKey | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // Fetch API keys
  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => apiKeysService.listApiKeys(),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (keyId: string) => apiKeysService.deleteApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      message.success('API key revoked successfully');
    },
    onError: (error) => {
      message.error(getErrorMessage(error));
    },
  });

  // Rotate mutation
  const rotateMutation = useMutation({
    mutationFn: (keyId: string) => apiKeysService.rotateApiKey(keyId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setNewKeyValue(data.key);
      message.success('API key rotated successfully');
    },
    onError: (error) => {
      message.error(getErrorMessage(error));
    },
  });

  const handleCreate = () => {
    setSelectedKey(null);
    setIsCreating(true);
    setModalOpen(true);
  };

  const handleEdit = (key: APIKey) => {
    setSelectedKey(key);
    setIsCreating(false);
    setModalOpen(true);
  };

  const handleModalClose = (newKey?: string) => {
    setModalOpen(false);
    setSelectedKey(null);
    setIsCreating(false);
    if (newKey) {
      setNewKeyValue(newKey);
    }
  };

  const handleCopyKey = async () => {
    if (newKeyValue) {
      await navigator.clipboard.writeText(newKeyValue);
      setCopiedKey(true);
      message.success('API key copied to clipboard');
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const handleCloseKeyModal = () => {
    setNewKeyValue(null);
    setCopiedKey(false);
  };

  const formatDate = (date: string | null) => {
    if (!date) return '-';
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatDateTime = (date: string | null) => {
    if (!date) return 'Never';
    return new Date(date).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  const isExpiringSoon = (expiresAt: string | null) => {
    if (!expiresAt) return false;
    const expiry = new Date(expiresAt);
    const now = new Date();
    const daysUntilExpiry = (expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
    return daysUntilExpiry > 0 && daysUntilExpiry <= 7;
  };

  const columns: ColumnsType<APIKey> = [
    {
      title: 'Name',
      key: 'name',
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.name}</div>
          <Text type="secondary" style={{ fontSize: 12 }} copyable>
            {record.key_prefix}...
          </Text>
        </div>
      ),
    },
    {
      title: 'Scopes',
      key: 'scopes',
      width: 250,
      render: (_, record) => (
        <Space wrap size={[4, 4]}>
          {record.scopes.includes('*') ? (
            <Tag color="red">Full Access</Tag>
          ) : (
            <>
              {record.scopes.slice(0, 3).map((scope) => (
                <Tag key={scope} style={{ fontSize: 11 }}>
                  {scope.replace(/:/g, ' ').replace(/_/g, ' ')}
                </Tag>
              ))}
              {record.scopes.length > 3 && (
                <Tooltip title={record.scopes.slice(3).join(', ')}>
                  <Tag style={{ fontSize: 11 }}>+{record.scopes.length - 3} more</Tag>
                </Tooltip>
              )}
            </>
          )}
        </Space>
      ),
    },
    {
      title: 'Rate Limit',
      key: 'rate_limit',
      width: 100,
      render: (_, record) => (
        <Text>{record.rate_limit}/min</Text>
      ),
    },
    {
      title: 'Expires',
      key: 'expires_at',
      width: 120,
      render: (_, record) => {
        if (!record.expires_at) {
          return <Text type="secondary">Never</Text>;
        }
        if (isExpired(record.expires_at)) {
          return (
            <Tag color="red" icon={<WarningOutlined />}>
              Expired
            </Tag>
          );
        }
        if (isExpiringSoon(record.expires_at)) {
          return (
            <Tooltip title={formatDate(record.expires_at)}>
              <Tag color="orange" icon={<WarningOutlined />}>
                Expiring soon
              </Tag>
            </Tooltip>
          );
        }
        return <Text>{formatDate(record.expires_at)}</Text>;
      },
    },
    {
      title: 'Last Used',
      key: 'last_used_at',
      width: 150,
      render: (_, record) => (
        <Tooltip title={record.usage_count > 0 ? `${record.usage_count} total requests` : undefined}>
          <Text type="secondary">{formatDateTime(record.last_used_at)}</Text>
        </Tooltip>
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

          <Popconfirm
            title="Rotate this key?"
            description="The old key will be immediately invalidated. You will receive a new key."
            onConfirm={() => rotateMutation.mutate(record.id)}
            okText="Rotate"
            cancelText="Cancel"
          >
            <Tooltip title="Rotate key">
              <Button
                size="small"
                icon={<SyncOutlined />}
                loading={rotateMutation.isPending}
              />
            </Tooltip>
          </Popconfirm>

          <Popconfirm
            title="Revoke this API key?"
            description="This will immediately invalidate the key. Any applications using it will fail."
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="Revoke"
            okButtonProps={{ danger: true }}
            cancelText="Cancel"
          >
            <Tooltip title="Revoke">
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                loading={deleteMutation.isPending}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <Text type="secondary">
            Manage API keys for programmatic access. API keys provide scoped access to your data.
          </Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          Create API Key
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={apiKeys || []}
        rowKey="id"
        loading={isLoading}
        pagination={false}
      />

      <ApiKeyModal
        apiKey={selectedKey}
        isCreating={isCreating}
        open={modalOpen}
        onClose={handleModalClose}
      />

      {/* New Key Display Modal */}
      <Modal
        title="API Key Created"
        open={!!newKeyValue}
        onCancel={handleCloseKeyModal}
        footer={[
          <Button
            key="copy"
            type="primary"
            icon={copiedKey ? <CheckOutlined /> : <CopyOutlined />}
            onClick={handleCopyKey}
          >
            {copiedKey ? 'Copied!' : 'Copy to Clipboard'}
          </Button>,
          <Button key="close" onClick={handleCloseKeyModal}>
            Close
          </Button>,
        ]}
      >
        <Alert
          type="warning"
          showIcon
          message="Save this key now"
          description="This is the only time you will see the full API key. Store it securely."
          style={{ marginBottom: 16 }}
        />
        <Paragraph
          code
          copyable={{
            text: newKeyValue || '',
            onCopy: () => {
              setCopiedKey(true);
              message.success('Copied!');
              setTimeout(() => setCopiedKey(false), 2000);
            },
          }}
          style={{
            background: '#f5f5f5',
            padding: 12,
            borderRadius: 4,
            wordBreak: 'break-all',
          }}
        >
          {newKeyValue}
        </Paragraph>
      </Modal>
    </div>
  );
}
