/**
 * Email configuration tab for Settings page
 */

import { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  Button,
  Card,
  Space,
  Typography,
  Switch,
  InputNumber,
  Alert,
  Modal,
  Tag,
  Spin,
  message,
  Row,
  Col,
} from 'antd';
import {
  MailOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SendOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import {
  useEmailConfigQuery,
  useSaveEmailConfigMutation,
  useTestEmailConfigMutation,
  EmailProvider,
} from '../../services/emailService';
import { getErrorMessage } from '../../services/api';

const { Title, Paragraph } = Typography;
const { Option } = Select;

// Provider display info
const providerInfo: Record<EmailProvider, { name: string; description: string }> = {
  smtp: {
    name: 'SMTP',
    description: 'Standard email protocol - works with any email server',
  },
  ses: {
    name: 'Amazon SES',
    description: 'AWS Simple Email Service - scalable and cost-effective',
  },
  graph: {
    name: 'Microsoft 365',
    description: 'Send via Microsoft Graph API using your M365 mailbox',
  },
  sendgrid: {
    name: 'SendGrid',
    description: 'Popular email API with excellent deliverability',
  },
};

export default function EmailTab() {
  const [form] = Form.useForm();
  const [testModalVisible, setTestModalVisible] = useState(false);
  const [testEmail, setTestEmail] = useState('');
  const [selectedProvider, setSelectedProvider] = useState<EmailProvider>('smtp');

  const { data: config, isLoading } = useEmailConfigQuery();
  const saveMutation = useSaveEmailConfigMutation();
  const testMutation = useTestEmailConfigMutation();

  // Populate form when config loads
  useEffect(() => {
    if (config) {
      setSelectedProvider(config.provider as EmailProvider);
      form.setFieldsValue({
        provider: config.provider,
        from_email: config.from_email,
        from_name: config.from_name,
        reply_to_email: config.reply_to_email,
        max_sends_per_hour: config.max_sends_per_hour,
        is_active: config.is_active,
      });
    }
  }, [config, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      // Build provider-specific config
      let providerConfig: Record<string, unknown> = {};

      if (selectedProvider === 'smtp') {
        providerConfig = {
          host: values.smtp_host,
          port: values.smtp_port,
          username: values.smtp_username,
          password: values.smtp_password,
          use_tls: values.smtp_use_tls ?? true,
          use_ssl: values.smtp_use_ssl ?? false,
        };
      } else if (selectedProvider === 'ses') {
        providerConfig = {
          region: values.ses_region,
          access_key_id: values.ses_access_key_id,
          secret_access_key: values.ses_secret_access_key,
          configuration_set: values.ses_configuration_set,
        };
      } else if (selectedProvider === 'graph') {
        providerConfig = {
          client_id: values.graph_client_id,
          client_secret: values.graph_client_secret,
          tenant_id: values.graph_tenant_id,
          user_id: values.graph_user_id,
        };
      } else if (selectedProvider === 'sendgrid') {
        providerConfig = {
          api_key: values.sendgrid_api_key,
        };
      }

      await saveMutation.mutateAsync({
        provider: selectedProvider,
        from_email: values.from_email,
        from_name: values.from_name,
        reply_to_email: values.reply_to_email,
        config: providerConfig,
        max_sends_per_hour: values.max_sends_per_hour,
        is_active: values.is_active,
      });

      message.success('Email configuration saved successfully');
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return; // Form validation error
      }
      message.error(getErrorMessage(error));
    }
  };

  const handleTest = async () => {
    if (!testEmail) {
      message.error('Please enter a test email address');
      return;
    }

    try {
      const result = await testMutation.mutateAsync(testEmail);
      if (result.success) {
        message.success(result.message);
        setTestModalVisible(false);
        setTestEmail('');
      } else {
        message.error(result.message);
      }
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={4}>
          <MailOutlined style={{ marginRight: 8 }} />
          Email Configuration
        </Title>
        <Paragraph type="secondary">
          Configure how Dewey sends emails for auto-responses, notifications, and campaigns.
        </Paragraph>
      </div>

      {config && (
        <Alert
          type={config.is_active ? 'success' : 'warning'}
          message={
            <Space>
              {config.is_active ? (
                <>
                  <CheckCircleOutlined />
                  <span>Email sending is enabled</span>
                  <Tag color="blue">{providerInfo[config.provider as EmailProvider]?.name}</Tag>
                </>
              ) : (
                <>
                  <CloseCircleOutlined />
                  <span>Email sending is disabled</span>
                </>
              )}
            </Space>
          }
          style={{ marginBottom: 24 }}
        />
      )}

      {config?.last_error && (
        <Alert
          type="error"
          message="Last Error"
          description={config.last_error}
          style={{ marginBottom: 24 }}
        />
      )}

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          provider: 'smtp',
          max_sends_per_hour: 100,
          is_active: true,
          smtp_port: 587,
          smtp_use_tls: true,
          smtp_use_ssl: false,
        }}
      >
        <Card title="Provider Selection" style={{ marginBottom: 24 }}>
          <Form.Item
            name="provider"
            label="Email Provider"
            rules={[{ required: true, message: 'Please select a provider' }]}
            extra={providerInfo[selectedProvider]?.description}
          >
            <Select
              size="large"
              onChange={(value) => setSelectedProvider(value as EmailProvider)}
            >
              {Object.entries(providerInfo).map(([key, info]) => (
                <Option key={key} value={key}>
                  {info.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Card>

        <Card title="Sender Information" style={{ marginBottom: 24 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="from_email"
                label="From Email"
                rules={[
                  { required: true, message: 'Please enter sender email' },
                  { type: 'email', message: 'Please enter a valid email' },
                ]}
              >
                <Input placeholder="noreply@yourcompany.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="from_name" label="From Name">
                <Input placeholder="Your Company Name" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="reply_to_email"
            label="Reply-To Email"
            rules={[{ type: 'email', message: 'Please enter a valid email' }]}
          >
            <Input placeholder="support@yourcompany.com (optional)" />
          </Form.Item>
        </Card>

        {/* SMTP Configuration */}
        {selectedProvider === 'smtp' && (
          <Card
            title={
              <Space>
                <SettingOutlined />
                SMTP Configuration
              </Space>
            }
            style={{ marginBottom: 24 }}
          >
            <Row gutter={16}>
              <Col span={16}>
                <Form.Item
                  name="smtp_host"
                  label="SMTP Host"
                  rules={[{ required: true, message: 'Please enter SMTP host' }]}
                >
                  <Input placeholder="smtp.example.com" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="smtp_port"
                  label="Port"
                  rules={[{ required: true, message: 'Please enter port' }]}
                >
                  <InputNumber style={{ width: '100%' }} min={1} max={65535} />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="smtp_username" label="Username">
                  <Input placeholder="Username or email" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="smtp_password" label="Password">
                  <Input.Password placeholder="Password or app-specific password" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="smtp_use_tls"
                  label="Use TLS (STARTTLS)"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="smtp_use_ssl"
                  label="Use SSL/TLS (Implicit)"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
              </Col>
            </Row>

            <Alert
              type="info"
              message="Common SMTP Settings"
              description={
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>Gmail: smtp.gmail.com, port 587, TLS enabled</li>
                  <li>Outlook/M365: smtp.office365.com, port 587, TLS enabled</li>
                  <li>Amazon SES SMTP: email-smtp.{'{region}'}.amazonaws.com, port 587</li>
                </ul>
              }
            />
          </Card>
        )}

        {/* AWS SES Configuration */}
        {selectedProvider === 'ses' && (
          <Card
            title={
              <Space>
                <SettingOutlined />
                AWS SES Configuration
              </Space>
            }
            style={{ marginBottom: 24 }}
          >
            <Form.Item
              name="ses_region"
              label="AWS Region"
              rules={[{ required: true, message: 'Please enter AWS region' }]}
            >
              <Select placeholder="Select region">
                <Option value="us-east-1">US East (N. Virginia)</Option>
                <Option value="us-east-2">US East (Ohio)</Option>
                <Option value="us-west-2">US West (Oregon)</Option>
                <Option value="eu-west-1">Europe (Ireland)</Option>
                <Option value="eu-central-1">Europe (Frankfurt)</Option>
                <Option value="ap-southeast-1">Asia Pacific (Singapore)</Option>
                <Option value="ap-southeast-2">Asia Pacific (Sydney)</Option>
              </Select>
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="ses_access_key_id"
                  label="Access Key ID"
                  rules={[{ required: true, message: 'Please enter access key' }]}
                >
                  <Input placeholder="AKIAIOSFODNN7EXAMPLE" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="ses_secret_access_key"
                  label="Secret Access Key"
                  rules={[{ required: true, message: 'Please enter secret key' }]}
                >
                  <Input.Password placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="ses_configuration_set" label="Configuration Set (Optional)">
              <Input placeholder="my-configuration-set" />
            </Form.Item>
          </Card>
        )}

        {/* Microsoft Graph Configuration */}
        {selectedProvider === 'graph' && (
          <Card
            title={
              <Space>
                <SettingOutlined />
                Microsoft 365 Configuration
              </Space>
            }
            style={{ marginBottom: 24 }}
          >
            <Alert
              type="info"
              message="Azure AD App Registration Required"
              description="Create an app registration in Azure AD with Mail.Send permission (application type)."
              style={{ marginBottom: 16 }}
            />

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="graph_tenant_id"
                  label="Azure Tenant ID"
                  rules={[{ required: true, message: 'Please enter tenant ID' }]}
                >
                  <Input placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="graph_client_id"
                  label="Application (Client) ID"
                  rules={[{ required: true, message: 'Please enter client ID' }]}
                >
                  <Input placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="graph_client_secret"
              label="Client Secret"
              rules={[{ required: true, message: 'Please enter client secret' }]}
            >
              <Input.Password placeholder="Client secret value" />
            </Form.Item>

            <Form.Item
              name="graph_user_id"
              label="Send As (Mailbox)"
              rules={[
                { required: true, message: 'Please enter mailbox email' },
                { type: 'email', message: 'Please enter a valid email' },
              ]}
              extra="The mailbox to send emails from (e.g., noreply@yourcompany.com)"
            >
              <Input placeholder="noreply@yourcompany.com" />
            </Form.Item>
          </Card>
        )}

        {/* SendGrid Configuration */}
        {selectedProvider === 'sendgrid' && (
          <Card
            title={
              <Space>
                <SettingOutlined />
                SendGrid Configuration
              </Space>
            }
            style={{ marginBottom: 24 }}
          >
            <Form.Item
              name="sendgrid_api_key"
              label="API Key"
              rules={[{ required: true, message: 'Please enter API key' }]}
              extra="Create an API key at sendgrid.com with Mail Send permission"
            >
              <Input.Password placeholder="SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
            </Form.Item>
          </Card>
        )}

        <Card title="Settings" style={{ marginBottom: 24 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="max_sends_per_hour"
                label="Max Emails Per Hour"
                extra="Rate limit to prevent abuse"
              >
                <InputNumber style={{ width: '100%' }} min={1} max={10000} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="is_active"
                label="Enable Email Sending"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Space>
          <Button
            type="primary"
            size="large"
            onClick={handleSave}
            loading={saveMutation.isPending}
          >
            Save Configuration
          </Button>

          {config && (
            <Button
              size="large"
              icon={<SendOutlined />}
              onClick={() => setTestModalVisible(true)}
            >
              Send Test Email
            </Button>
          )}
        </Space>
      </Form>

      {/* Test Email Modal */}
      <Modal
        title="Send Test Email"
        open={testModalVisible}
        onOk={handleTest}
        onCancel={() => {
          setTestModalVisible(false);
          setTestEmail('');
        }}
        confirmLoading={testMutation.isPending}
        okText="Send Test"
      >
        <Paragraph>
          Send a test email to verify your configuration is working correctly.
        </Paragraph>
        <Form.Item label="Recipient Email" required>
          <Input
            type="email"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
            placeholder="your-email@example.com"
          />
        </Form.Item>
      </Modal>
    </div>
  );
}
