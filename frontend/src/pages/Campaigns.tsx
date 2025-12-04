import { Typography } from 'antd';

const { Title, Paragraph } = Typography;

export default function Campaigns() {
  return (
    <div>
      <Title level={2}>Campaigns</Title>
      <Paragraph>
        Detected coordinated/template message campaigns.
      </Paragraph>
      <Paragraph type="secondary">
        This page will include:
        <ul>
          <li>Active campaigns list with message counts</li>
          <li>Campaign timeline visualization</li>
          <li>Geographic distribution of senders</li>
          <li>Template preview</li>
          <li>Confirm/dismiss/merge actions</li>
          <li>Bulk response functionality</li>
        </ul>
      </Paragraph>
    </div>
  );
}
