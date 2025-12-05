import { useState } from 'react';
import { Typography, Tabs, Card } from 'antd';
import {
  UserOutlined,
  TeamOutlined,
  KeyOutlined,
  SettingOutlined,
  CloudOutlined,
  MailOutlined,
  CreditCardOutlined,
} from '@ant-design/icons';
import UsersTab from '../components/settings/UsersTab';
import RolesTab from '../components/settings/RolesTab';
import ApiKeysTab from '../components/settings/ApiKeysTab';
import EmailTab from '../components/settings/EmailTab';

const { Title, Paragraph, Text } = Typography;

// Placeholder component for tabs not yet implemented
function ComingSoon({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <Paragraph type="secondary">
        {title} settings will include:
      </Paragraph>
      <ul>
        {items.map((item, index) => (
          <li key={index}>
            <Text type="secondary">{item}</Text>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState('users');

  const tabItems = [
    {
      key: 'users',
      label: (
        <span>
          <UserOutlined style={{ marginRight: 8 }} />
          Users
        </span>
      ),
      children: <UsersTab />,
    },
    {
      key: 'roles',
      label: (
        <span>
          <TeamOutlined style={{ marginRight: 8 }} />
          Roles
        </span>
      ),
      children: <RolesTab />,
    },
    {
      key: 'api-keys',
      label: (
        <span>
          <KeyOutlined style={{ marginRight: 8 }} />
          API Keys
        </span>
      ),
      children: <ApiKeysTab />,
    },
    {
      key: 'integrations',
      label: (
        <span>
          <CloudOutlined style={{ marginRight: 8 }} />
          Integrations
        </span>
      ),
      children: (
        <ComingSoon
          title="Integration"
          items={[
            'Microsoft 365 / Azure AD configuration',
            'AI provider settings (Claude, OpenAI)',
            'Webhook configurations',
            'Third-party app connections',
          ]}
        />
      ),
    },
    {
      key: 'email',
      label: (
        <span>
          <MailOutlined style={{ marginRight: 8 }} />
          Email
        </span>
      ),
      children: <EmailTab />,
    },
    {
      key: 'general',
      label: (
        <span>
          <SettingOutlined style={{ marginRight: 8 }} />
          General
        </span>
      ),
      children: (
        <ComingSoon
          title="General"
          items={[
            'Organization name and branding',
            'Timezone and locale settings',
            'Custom field definitions',
            'Data retention policies',
          ]}
        />
      ),
    },
    {
      key: 'billing',
      label: (
        <span>
          <CreditCardOutlined style={{ marginRight: 8 }} />
          Billing
        </span>
      ),
      children: (
        <ComingSoon
          title="Billing"
          items={[
            'Current subscription plan',
            'Usage metrics and limits',
            'Payment methods',
            'Invoice history',
          ]}
        />
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>Settings</Title>
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          tabPosition="left"
          style={{ minHeight: 500 }}
        />
      </Card>
    </div>
  );
}
