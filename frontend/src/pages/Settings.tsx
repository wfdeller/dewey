import { Typography } from 'antd';

const { Title, Paragraph } = Typography;

export default function Settings() {
  return (
    <div>
      <Title level={2}>Settings</Title>
      <Paragraph>
        Tenant configuration and administration.
      </Paragraph>
      <Paragraph type="secondary">
        This page will include:
        <ul>
          <li>User management (invite, roles, permissions)</li>
          <li>Role configuration with Azure AD group sync</li>
          <li>API key management</li>
          <li>Custom field definitions</li>
          <li>AI provider configuration</li>
          <li>Microsoft 365 integration settings</li>
          <li>Email/IMAP configuration</li>
          <li>Billing and subscription</li>
        </ul>
      </Paragraph>
    </div>
  );
}
