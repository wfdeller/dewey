import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Tag,
  Spin,
  Alert,
  Button,
  Row,
  Col,
  Divider,
  Typography,
  Space,
} from 'antd';
import {
  ArrowLeftOutlined,
  UserOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useMessage } from '../hooks/useMessages';
import type { SentimentLabel } from '../types';

const { Title, Paragraph, Text } = Typography;

const sentimentColors: Record<SentimentLabel, string> = {
  positive: 'green',
  neutral: 'gold',
  negative: 'red',
};

export default function MessageDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: message, isLoading, error } = useMessage(id || '');

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error || !message) {
    return (
      <Alert
        message="Error loading message"
        description="Unable to load message details. Please try again later."
        type="error"
        showIcon
        action={
          <Button onClick={() => navigate('/messages')}>Back to Messages</Button>
        }
      />
    );
  }

  // Mock data for development
  const mockMessage = {
    id: id || '1',
    tenantId: '1',
    subject: 'Question about my account status',
    bodyText: `Hello,

I hope this message finds you well. I'm writing to inquire about the current status of my account. I noticed some discrepancies in my recent statement and would appreciate some clarification.

Specifically, I have questions about:
1. The service charges applied on November 15th
2. The adjustment made to my subscription tier
3. The timeline for my pending refund request

I've been a loyal customer for over 5 years and have always appreciated your excellent service. I trust that you'll be able to help me resolve these questions.

Thank you for your time and assistance.

Best regards,
John Doe`,
    bodyHtml: null,
    senderEmail: 'john.doe@example.com',
    senderName: 'John Doe',
    source: 'email' as const,
    processingStatus: 'completed' as const,
    isTemplateMatch: false,
    receivedAt: new Date(Date.now() - 3600000).toISOString(),
    processedAt: new Date(Date.now() - 3500000).toISOString(),
    analysis: {
      id: '1',
      messageId: id || '1',
      sentimentScore: 0.35,
      sentimentLabel: 'positive' as const,
      sentimentConfidence: 0.92,
      summary: 'Long-time customer inquiring about account discrepancies including service charges, subscription changes, and a pending refund. Tone is polite and constructive.',
      entities: [
        { type: 'person' as const, value: 'John Doe', confidence: 0.98 },
        { type: 'topic' as const, value: 'Account Status', confidence: 0.95 },
        { type: 'topic' as const, value: 'Service Charges', confidence: 0.88 },
        { type: 'topic' as const, value: 'Refund', confidence: 0.85 },
      ],
      suggestedCategories: [
        { categoryId: 'cat-1', confidence: 0.91 },
        { categoryId: 'cat-2', confidence: 0.75 },
      ],
      suggestedResponse: 'Thank you for reaching out regarding your account. We appreciate your 5 years of loyalty. I\'d be happy to review the charges and adjustments you mentioned. Let me look into your account and I\'ll provide a detailed response within 24 hours.',
      urgencyScore: 0.45,
      aiProvider: 'claude',
      aiModel: 'claude-3-sonnet-20240229',
    },
  };

  const displayMessage = message || mockMessage;
  const analysis = displayMessage.analysis;

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/messages')}
        style={{ marginBottom: 16 }}
      >
        Back to Messages
      </Button>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card>
            <Title level={4}>{displayMessage.subject}</Title>

            <Descriptions column={2} style={{ marginBottom: 24 }}>
              <Descriptions.Item label={<><UserOutlined /> From</>}>
                {displayMessage.sender_name || displayMessage.sender_email}
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  {displayMessage.sender_email}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label={<><ClockCircleOutlined /> Received</>}>
                {dayjs(displayMessage.received_at).format('MMMM D, YYYY h:mm A')}
              </Descriptions.Item>
              <Descriptions.Item label="Source">
                <Tag color="blue">{displayMessage.source.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={displayMessage.processing_status === 'completed' ? 'success' : 'processing'}>
                  {displayMessage.processing_status}
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
              {displayMessage.body_text}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {analysis && (
            <>
              <Card title="AI Analysis" style={{ marginBottom: 16 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text type="secondary">Sentiment</Text>
                    <div>
                      <Tag color={sentimentColors[analysis.sentiment_label]} style={{ marginTop: 4 }}>
                        {analysis.sentiment_label.toUpperCase()}
                      </Tag>
                      <Text style={{ marginLeft: 8 }}>
                        Score: {analysis.sentiment_score.toFixed(2)}
                      </Text>
                      <Text type="secondary" style={{ marginLeft: 8 }}>
                        ({(analysis.sentiment_confidence * 100).toFixed(0)}% confidence)
                      </Text>
                    </div>
                  </div>

                  <div>
                    <Text type="secondary">Urgency</Text>
                    <div>
                      <Tag color={analysis.urgency_score > 0.7 ? 'red' : analysis.urgency_score > 0.4 ? 'gold' : 'green'}>
                        {analysis.urgency_score > 0.7 ? 'HIGH' : analysis.urgency_score > 0.4 ? 'MEDIUM' : 'LOW'}
                      </Tag>
                      <Text style={{ marginLeft: 8 }}>
                        {(analysis.urgency_score * 100).toFixed(0)}%
                      </Text>
                    </div>
                  </div>

                  <Divider style={{ margin: '12px 0' }} />

                  <div>
                    <Text type="secondary">Summary</Text>
                    <Paragraph style={{ marginTop: 4 }}>{analysis.summary}</Paragraph>
                  </div>
                </Space>
              </Card>

              <Card title="Entities Detected" style={{ marginBottom: 16 }}>
                {analysis.entities.length > 0 ? (
                  <Space wrap>
                    {analysis.entities.map((entity, idx) => (
                      <Tag key={idx} color={
                        entity.type === 'person' ? 'blue' :
                        entity.type === 'org' ? 'green' :
                        entity.type === 'location' ? 'orange' : 'purple'
                      }>
                        {entity.value}
                      </Tag>
                    ))}
                  </Space>
                ) : (
                  <Text type="secondary">No entities detected</Text>
                )}
              </Card>

              {analysis.suggested_response && (
                <Card title="Suggested Response">
                  <Paragraph>{analysis.suggested_response}</Paragraph>
                  <Button type="primary" style={{ marginTop: 8 }}>
                    Use This Response
                  </Button>
                </Card>
              )}
            </>
          )}
        </Col>
      </Row>
    </div>
  );
}
