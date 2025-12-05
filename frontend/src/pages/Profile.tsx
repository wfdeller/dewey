import { Typography, Card, Descriptions, Tag, Space, Divider, Empty } from 'antd';
import {
  UserOutlined,
  MailOutlined,
  TeamOutlined,
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';

const { Title, Text } = Typography;

export default function Profile() {
  const user = useAuthStore((state) => state.user);

  if (!user) {
    return (
      <div style={{ padding: 24 }}>
        <Empty description="User information not available" />
      </div>
    );
  }

  return (
    <div>
      <Title level={2}>My Profile</Title>
      <Text type="secondary">
        View your account details and organization information.
      </Text>

      <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
        {/* User Information Card */}
        <Card
          title={
            <Space>
              <UserOutlined />
              <span>Account Information</span>
            </Space>
          }
        >
          <Descriptions column={1} labelStyle={{ fontWeight: 500 }}>
            <Descriptions.Item label="Name">{user.name}</Descriptions.Item>
            <Descriptions.Item label="Email">
              <Space>
                <MailOutlined />
                {user.email}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="User ID">
              <Text code copyable={{ text: user.id }}>
                {user.id}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Account Status">
              {user.isActive ? (
                <Tag icon={<CheckCircleOutlined />} color="success">
                  Active
                </Tag>
              ) : (
                <Tag icon={<CloseCircleOutlined />} color="error">
                  Inactive
                </Tag>
              )}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        {/* Tenant/Organization Card */}
        <Card
          title={
            <Space>
              <TeamOutlined />
              <span>Organization</span>
            </Space>
          }
        >
          <Descriptions column={1} labelStyle={{ fontWeight: 500 }}>
            <Descriptions.Item label="Tenant Name">
              <Text strong>{user.tenantName}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Tenant Slug">
              <Text code>{user.tenantSlug}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Tenant ID">
              <Text code copyable={{ text: user.tenantId }}>
                {user.tenantId}
              </Text>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        {/* Roles & Permissions Card */}
        <Card
          title={
            <Space>
              <SafetyCertificateOutlined />
              <span>Roles &amp; Permissions</span>
            </Space>
          }
        >
          <div style={{ marginBottom: 16 }}>
            <Text strong>Roles:</Text>
            <div style={{ marginTop: 8 }}>
              {user.roles.length > 0 ? (
                <Space wrap>
                  {user.roles.map((role) => (
                    <Tag key={role} color="blue">
                      {role}
                    </Tag>
                  ))}
                </Space>
              ) : (
                <Text type="secondary">No roles assigned</Text>
              )}
            </div>
          </div>

          <Divider style={{ margin: '16px 0' }} />

          <div>
            <Text strong>Permissions:</Text>
            <div style={{ marginTop: 8 }}>
              {user.permissions.length > 0 ? (
                <Space wrap>
                  {user.permissions.map((permission) => (
                    <Tag key={permission}>{permission}</Tag>
                  ))}
                </Space>
              ) : (
                <Text type="secondary">No explicit permissions</Text>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
