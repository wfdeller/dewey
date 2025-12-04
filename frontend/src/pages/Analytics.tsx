import { Typography } from 'antd';

const { Title, Paragraph } = Typography;

export default function Analytics() {
  return (
    <div>
      <Title level={2}>Analytics</Title>
      <Paragraph>
        Comprehensive reporting and analytics dashboard.
      </Paragraph>
      <Paragraph type="secondary">
        This page will include:
        <ul>
          <li>Sentiment trends over time</li>
          <li>Message volume charts</li>
          <li>Category distribution</li>
          <li>Top contacts leaderboard</li>
          <li>Custom field breakdowns</li>
          <li>Campaign vs organic comparison</li>
          <li>Date range and filter controls</li>
          <li>Export to CSV/PDF</li>
        </ul>
      </Paragraph>
    </div>
  );
}
