import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Typography,
    Button,
    Space,
    Card,
    Tabs,
    Input,
    Alert,
    Spin,
    Empty,
    message,
    Row,
    Col,
    Divider,
    InputNumber,
} from 'antd';
import { ArrowLeftOutlined, CopyOutlined, LinkOutlined, CodeOutlined, Html5Outlined } from '@ant-design/icons';
import { useFormQuery } from '../services/formsService';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

export default function FormEmbed() {
    const { formId } = useParams<{ formId: string }>();
    const navigate = useNavigate();
    const [iframeWidth, setIframeWidth] = useState(600);
    const [iframeHeight, setIframeHeight] = useState(800);

    const { data: form, isLoading } = useFormQuery(formId || '');

    // Construct URLs
    const baseUrl = window.location.origin;
    const tenantSlug = 'demo'; // TODO: Get from user/tenant
    const directLink = form ? `${baseUrl}/f/${tenantSlug}/${form.slug}` : '';

    const iframeCode = form
        ? `<iframe
  src="${directLink}"
  width="${iframeWidth}"
  height="${iframeHeight}"
  frameborder="0"
  style="border: none; max-width: 100%;">
</iframe>`
        : '';

    const scriptCode = form
        ? `<div data-dewey-form="${tenantSlug}/${form.slug}"></div>
<script src="${baseUrl}/forms/embed.js" async></script>`
        : '';

    const copyToClipboard = (text: string, label: string) => {
        navigator.clipboard.writeText(text);
        message.success(`${label} copied to clipboard`);
    };

    if (isLoading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
                <Spin size='large' />
            </div>
        );
    }

    if (!form) {
        return (
            <Empty description='Form not found'>
                <Button onClick={() => navigate('/forms')}>Back to Forms</Button>
            </Empty>
        );
    }

    if (form.status !== 'published') {
        return (
            <div>
                <div style={{ marginBottom: 24 }}>
                    <Space>
                        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/forms')}>
                            Back
                        </Button>
                        <Title level={3} style={{ margin: 0 }}>
                            {form.name} - Embed
                        </Title>
                    </Space>
                </div>

                <Alert
                    type='warning'
                    message='Form Not Published'
                    description="You need to publish this form before you can embed it. Go to the form builder and click 'Publish'."
                    showIcon
                />
            </div>
        );
    }

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space>
                    <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/forms')}>
                        Back
                    </Button>
                    <Title level={3} style={{ margin: 0 }}>
                        {form.name} - Embed Code
                    </Title>
                </Space>
            </div>

            <Tabs
                items={[
                    {
                        key: 'link',
                        label: (
                            <span>
                                <LinkOutlined /> Direct Link
                            </span>
                        ),
                        children: (
                            <Card>
                                <Paragraph>
                                    Share this link directly with your audience. They can fill out the form on a
                                    dedicated page hosted by Dewey.
                                </Paragraph>

                                <Input.Group compact style={{ display: 'flex', marginBottom: 16 }}>
                                    <Input value={directLink} readOnly style={{ flex: 1 }} />
                                    <Button
                                        type='primary'
                                        icon={<CopyOutlined />}
                                        onClick={() => copyToClipboard(directLink, 'Link')}
                                    >
                                        Copy
                                    </Button>
                                </Input.Group>

                                <Button type='link' onClick={() => window.open(directLink, '_blank')}>
                                    Open in new tab
                                </Button>
                            </Card>
                        ),
                    },
                    {
                        key: 'iframe',
                        label: (
                            <span>
                                <Html5Outlined /> iFrame Embed
                            </span>
                        ),
                        children: (
                            <Card>
                                <Paragraph>
                                    Embed the form on your website using an iFrame. This is the simplest embedding
                                    method and works with any website.
                                </Paragraph>

                                <Row gutter={16} style={{ marginBottom: 16 }}>
                                    <Col span={12}>
                                        <Text>Width (px)</Text>
                                        <InputNumber
                                            value={iframeWidth}
                                            onChange={(v) => setIframeWidth(v || 600)}
                                            min={300}
                                            max={2000}
                                            style={{ width: '100%' }}
                                        />
                                    </Col>
                                    <Col span={12}>
                                        <Text>Height (px)</Text>
                                        <InputNumber
                                            value={iframeHeight}
                                            onChange={(v) => setIframeHeight(v || 800)}
                                            min={300}
                                            max={2000}
                                            style={{ width: '100%' }}
                                        />
                                    </Col>
                                </Row>

                                <div style={{ marginBottom: 16 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                        <Text strong>Embed Code</Text>
                                        <Button
                                            size='small'
                                            icon={<CopyOutlined />}
                                            onClick={() => copyToClipboard(iframeCode, 'iFrame code')}
                                        >
                                            Copy
                                        </Button>
                                    </div>
                                    <TextArea
                                        value={iframeCode}
                                        readOnly
                                        rows={6}
                                        style={{ fontFamily: 'monospace', fontSize: 12 }}
                                    />
                                </div>

                                <Divider>Preview</Divider>

                                <div
                                    style={{
                                        border: '1px solid #d9d9d9',
                                        borderRadius: 4,
                                        padding: 16,
                                        background: '#fafafa',
                                        textAlign: 'center',
                                    }}
                                >
                                    <div
                                        style={{
                                            width: Math.min(iframeWidth, 500),
                                            height: 200,
                                            background: '#fff',
                                            border: '1px dashed #d9d9d9',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            margin: '0 auto',
                                        }}
                                    >
                                        <Text type='secondary'>
                                            Form preview ({iframeWidth}x{iframeHeight})
                                        </Text>
                                    </div>
                                </div>
                            </Card>
                        ),
                    },
                    {
                        key: 'script',
                        label: (
                            <span>
                                <CodeOutlined /> JavaScript Widget
                            </span>
                        ),
                        children: (
                            <Card>
                                <Paragraph>
                                    Embed the form using our JavaScript widget. This provides a more seamless
                                    integration and automatically adjusts to your page's styling.
                                </Paragraph>

                                <Alert
                                    type='info'
                                    message='Coming Soon'
                                    description='The JavaScript widget embedding is not yet available. Please use the iFrame or direct link option for now.'
                                    showIcon
                                    style={{ marginBottom: 16 }}
                                />

                                <div style={{ marginBottom: 16 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                        <Text strong>Embed Code</Text>
                                        <Button
                                            size='small'
                                            icon={<CopyOutlined />}
                                            onClick={() => copyToClipboard(scriptCode, 'Widget code')}
                                        >
                                            Copy
                                        </Button>
                                    </div>
                                    <TextArea
                                        value={scriptCode}
                                        readOnly
                                        rows={4}
                                        style={{ fontFamily: 'monospace', fontSize: 12 }}
                                    />
                                </div>

                                <Text type='secondary'>
                                    Add this code anywhere on your page where you want the form to appear. The script
                                    will automatically render the form in place of the div element.
                                </Text>
                            </Card>
                        ),
                    },
                ]}
            />
        </div>
    );
}
