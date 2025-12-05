import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import {
  Typography,
  Button,
  Space,
  Card,
  Tabs,
  Empty,
  Spin,
  message,
  Tag,
  Input,
  Form,
  Switch,
  InputNumber,
  Select,
  Drawer,
  Collapse,
  Tooltip,
  Alert,
  Row,
  Col,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  EyeOutlined,
  SettingOutlined,
  CodeOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import {
  useEmailTemplateQuery,
  useUpdateEmailTemplateMutation,
  useTemplateVariablesQuery,
  usePreviewTemplateMutation,
} from '../services/emailService';
import { useFormsQuery } from '../services/formsService';
import { getErrorMessage } from '../services/api';

const { Title, Text, Paragraph } = Typography;

// Quill editor modules configuration
const quillModules = {
  toolbar: [
    [{ header: [1, 2, 3, false] }],
    ['bold', 'italic', 'underline', 'strike'],
    [{ color: [] }, { background: [] }],
    [{ list: 'ordered' }, { list: 'bullet' }],
    [{ indent: '-1' }, { indent: '+1' }],
    [{ align: [] }],
    ['link', 'image'],
    ['clean'],
  ],
};

const quillFormats = [
  'header',
  'bold',
  'italic',
  'underline',
  'strike',
  'color',
  'background',
  'list',
  'bullet',
  'indent',
  'align',
  'link',
  'image',
];

export default function EmailTemplateEditor() {
  const { templateId } = useParams<{ templateId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('edit');
  const [settingsDrawerOpen, setSettingsDrawerOpen] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Form state
  const [subject, setSubject] = useState('');
  const [bodyHtml, setBodyHtml] = useState('');
  const [bodyText, setBodyText] = useState('');

  // Settings form
  const [settingsForm] = Form.useForm();

  // Preview state
  const [previewHtml, setPreviewHtml] = useState('');

  // Queries
  const { data: template, isLoading, refetch } = useEmailTemplateQuery(templateId || '');
  const { data: variablesData } = useTemplateVariablesQuery();
  const { data: formsData } = useFormsQuery();
  const updateMutation = useUpdateEmailTemplateMutation();
  const previewMutation = usePreviewTemplateMutation();

  // Initialize form when template loads
  useEffect(() => {
    if (template) {
      setSubject(template.subject);
      setBodyHtml(template.body_html);
      setBodyText(template.body_text || '');
      settingsForm.setFieldsValue({
        name: template.name,
        description: template.description,
        is_active: template.is_active,
        defaultFormId: template.default_form_id,
        formLinkSingleUse: template.form_link_single_use,
        formLinkExpiresDays: template.form_link_expires_days,
      });
    }
  }, [template, settingsForm]);

  const handleSubjectChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSubject(e.target.value);
    setHasUnsavedChanges(true);
  }, []);

  const handleBodyChange = useCallback((content: string) => {
    setBodyHtml(content);
    setHasUnsavedChanges(true);
  }, []);

  const handleSave = async () => {
    if (!templateId) return;

    try {
      const settingsValues = settingsForm.getFieldsValue();
      await updateMutation.mutateAsync({
        templateId,
        data: {
          name: settingsValues.name,
          description: settingsValues.description,
          subject,
          body_html: bodyHtml,
          body_text: bodyText || undefined,
          is_active: settingsValues.is_active,
          default_form_id: settingsValues.default_form_id || undefined,
          form_link_single_use: settingsValues.form_link_single_use,
          form_link_expires_days: settingsValues.form_link_expires_days,
        },
      });
      message.success('Template saved successfully');
      setHasUnsavedChanges(false);
      refetch();
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  const handlePreview = async () => {
    try {
      const result = await previewMutation.mutateAsync({
        subject,
        body_html: bodyHtml,
        body_text: bodyText || undefined,
        sampleData: {
          contact_name: 'John Doe',
          contact_email: 'john.doe@example.com',
          form_name: 'Sample Form',
          form_link_url: 'https://example.com/f/sample/form?t=abc123',
        },
      });
      setPreviewHtml(result.body_html);
      setActiveTab('preview');
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  const insertVariable = useCallback((variable: string) => {
    // Copy to clipboard and show message
    navigator.clipboard.writeText(`{{ ${variable} }}`);
    message.success(`Copied {{ ${variable} }} to clipboard`);
  }, []);

  // Memoized variables panel
  const variablesPanel = useMemo(() => {
    if (!variablesData?.variables) return null;

    return (
      <Collapse
        size="small"
        items={Object.entries(variablesData.variables).map(([category, vars]) => ({
          key: category,
          label: <Text strong style={{ textTransform: 'capitalize' }}>{category}</Text>,
          children: (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {Object.entries(vars).map(([name, description]) => (
                <Tooltip key={name} title={description} placement="left">
                  <Button
                    size="small"
                    style={{ textAlign: 'left', justifyContent: 'flex-start' }}
                    icon={<CopyOutlined />}
                    onClick={() => insertVariable(name)}
                  >
                    <code style={{ fontSize: 11 }}>{name}</code>
                  </Button>
                </Tooltip>
              ))}
            </div>
          ),
        }))}
        defaultActiveKey={['contact', 'form']}
      />
    );
  }, [variablesData, insertVariable]);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!template) {
    return (
      <Empty description="Template not found">
        <Button onClick={() => navigate('/email-templates')}>Back to Templates</Button>
      </Empty>
    );
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/email-templates')}>
            Back
          </Button>
          <Title level={3} style={{ margin: 0 }}>{template.name}</Title>
          <Tag color={template.is_active ? 'green' : 'default'}>
            {template.is_active ? 'ACTIVE' : 'INACTIVE'}
          </Tag>
          {hasUnsavedChanges && (
            <Tag color="orange">Unsaved changes</Tag>
          )}
        </Space>

        <Space>
          <Button
            icon={<EyeOutlined />}
            onClick={handlePreview}
            loading={previewMutation.isPending}
          >
            Preview
          </Button>
          <Button
            icon={<SettingOutlined />}
            onClick={() => setSettingsDrawerOpen(true)}
          >
            Settings
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={updateMutation.isPending}
          >
            Save
          </Button>
        </Space>
      </div>

      {/* Main content */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'edit',
            label: 'Edit',
            children: (
              <div style={{ display: 'flex', gap: 24 }}>
                {/* Variables panel */}
                <Card
                  title="Variables"
                  size="small"
                  style={{ width: 240, flexShrink: 0 }}
                  styles={{ body: { padding: 8 } }}
                >
                  <Alert
                    type="info"
                    message="Click to copy"
                    description="Click any variable to copy it, then paste into your email."
                    style={{ marginBottom: 8 }}
                    showIcon
                  />
                  {variablesPanel}
                </Card>

                {/* Editor */}
                <Card style={{ flex: 1 }}>
                  <Form layout="vertical">
                    <Form.Item label="Subject Line" required>
                      <Input
                        size="large"
                        value={subject}
                        onChange={handleSubjectChange}
                        placeholder="Enter email subject..."
                      />
                    </Form.Item>

                    <Form.Item label="Email Body" required>
                      <div style={{ border: '1px solid #d9d9d9', borderRadius: 6 }}>
                        <ReactQuill
                          theme="snow"
                          value={bodyHtml}
                          onChange={handleBodyChange}
                          modules={quillModules}
                          formats={quillFormats}
                          style={{ minHeight: 400 }}
                        />
                      </div>
                    </Form.Item>
                  </Form>
                </Card>
              </div>
            ),
          },
          {
            key: 'preview',
            label: 'Preview',
            children: (
              <Card title="Email Preview">
                <div style={{ marginBottom: 16 }}>
                  <Text strong>Subject: </Text>
                  <Text>{subject}</Text>
                </div>
                <div
                  style={{
                    border: '1px solid #d9d9d9',
                    borderRadius: 6,
                    padding: 24,
                    background: '#fff',
                    minHeight: 400,
                  }}
                  dangerouslySetInnerHTML={{ __html: previewHtml || bodyHtml }}
                />
              </Card>
            ),
          },
          {
            key: 'html',
            label: (
              <span>
                <CodeOutlined style={{ marginRight: 4 }} />
                HTML
              </span>
            ),
            children: (
              <Card title="HTML Source">
                <Input.TextArea
                  value={bodyHtml}
                  onChange={(e) => {
                    setBodyHtml(e.target.value);
                    setHasUnsavedChanges(true);
                  }}
                  rows={20}
                  style={{ fontFamily: 'monospace', fontSize: 12 }}
                />
              </Card>
            ),
          },
          {
            key: 'text',
            label: 'Plain Text',
            children: (
              <Card
                title="Plain Text Version"
                extra={
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Optional fallback for email clients that don't support HTML
                  </Text>
                }
              >
                <Input.TextArea
                  value={bodyText}
                  onChange={(e) => {
                    setBodyText(e.target.value);
                    setHasUnsavedChanges(true);
                  }}
                  rows={20}
                  placeholder="Enter plain text version of your email..."
                  style={{ fontFamily: 'monospace' }}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Settings Drawer */}
      <Drawer
        title="Template Settings"
        open={settingsDrawerOpen}
        onClose={() => setSettingsDrawerOpen(false)}
        width={400}
        extra={
          <Button
            type="primary"
            onClick={() => {
              setHasUnsavedChanges(true);
              setSettingsDrawerOpen(false);
            }}
          >
            Done
          </Button>
        }
      >
        <Form form={settingsForm} layout="vertical">
          <Form.Item
            name="name"
            label="Template Name"
            rules={[{ required: true, message: 'Please enter a name' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} />
          </Form.Item>

          <Form.Item
            name="isActive"
            label="Active"
            valuePropName="checked"
            extra="Inactive templates cannot be used in workflows"
          >
            <Switch />
          </Form.Item>

          <Collapse
            items={[
              {
                key: 'form-link',
                label: 'Form Link Settings',
                children: (
                  <>
                    <Form.Item
                      name="defaultFormId"
                      label="Default Form"
                      extra="Form to use when generating {{ form_link_url }} variable"
                    >
                      <Select
                        allowClear
                        placeholder="Select a form"
                        options={formsData?.items.map((f) => ({
                          value: f.id,
                          label: f.name,
                        }))}
                      />
                    </Form.Item>

                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name="formLinkSingleUse"
                          label="Single Use Links"
                          valuePropName="checked"
                        >
                          <Switch />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name="formLinkExpiresDays"
                          label="Link Expiry (days)"
                        >
                          <InputNumber min={1} max={365} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                  </>
                ),
              },
            ]}
            style={{ marginTop: 16 }}
          />
        </Form>

        <div style={{ marginTop: 24 }}>
          <Paragraph type="secondary">
            <strong>Statistics</strong>
          </Paragraph>
          <Space direction="vertical" size={4}>
            <Text type="secondary">
              Sends: {template.send_count.toLocaleString()}
            </Text>
            <Text type="secondary">
              Last sent: {template.last_sent_at ? new Date(template.last_sent_at).toLocaleString() : 'Never'}
            </Text>
            <Text type="secondary">
              Created: {new Date(template.created_at).toLocaleDateString()}
            </Text>
            <Text type="secondary">
              Updated: {new Date(template.updated_at).toLocaleDateString()}
            </Text>
          </Space>
        </div>
      </Drawer>

      {/* Custom styles for Quill */}
      <style>{`
        .ql-container {
          min-height: 350px;
          font-size: 14px;
        }
        .ql-editor {
          min-height: 350px;
        }
      `}</style>
    </div>
  );
}
