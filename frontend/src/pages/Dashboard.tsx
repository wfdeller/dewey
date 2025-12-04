import { Row, Col, Card, Statistic, Spin, Alert } from 'antd';
import {
  MailOutlined,
  RiseOutlined,
  FallOutlined,
  FlagOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useDashboardStats } from '../hooks/useAnalytics';

export default function Dashboard() {
  const { data: stats, isLoading, error } = useDashboardStats();

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Error loading dashboard"
        description="Unable to load dashboard statistics. Please try again later."
        type="error"
        showIcon
      />
    );
  }

  // Mock data for now
  const mockStats = stats || {
    totalMessages: 12847,
    messagesThisWeek: 342,
    avgSentiment: 0.23,
    activeCampaigns: 3,
    pendingMessages: 47,
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.2) return '#52c41a';
    if (score < -0.2) return '#f5222d';
    return '#faad14';
  };

  const getSentimentLabel = (score: number) => {
    if (score > 0.2) return 'Positive';
    if (score < -0.2) return 'Negative';
    return 'Neutral';
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>Dashboard</h2>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Messages"
              value={mockStats.totalMessages}
              prefix={<MailOutlined />}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="This Week"
              value={mockStats.messagesThisWeek}
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Avg Sentiment"
              value={getSentimentLabel(mockStats.avgSentiment)}
              prefix={
                mockStats.avgSentiment > 0 ? <RiseOutlined /> : <FallOutlined />
              }
              valueStyle={{ color: getSentimentColor(mockStats.avgSentiment) }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Campaigns"
              value={mockStats.activeCampaigns}
              prefix={<FlagOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <Card title="Message Volume Trends">
            <div
              style={{
                height: 300,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#999',
              }}
            >
              Charts will be implemented with @ant-design/charts
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="Pending Messages" extra={<ClockCircleOutlined />}>
            <Statistic
              value={mockStats.pendingMessages}
              suffix="awaiting review"
            />
            <div style={{ marginTop: 16 }}>
              <a href="/messages?status=pending">View all pending →</a>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="Sentiment Distribution">
            <div
              style={{
                height: 250,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#999',
              }}
            >
              Pie chart will be implemented
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Top Categories">
            <div
              style={{
                height: 250,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#999',
              }}
            >
              Bar chart will be implemented
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
