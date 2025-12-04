import { Typography } from 'antd';

const { Title, Paragraph } = Typography;

export default function Contacts() {
  return (
    <div>
      <Title level={2}>Contacts</Title>
      <Paragraph>
        Contact management with custom fields, message history, and sentiment tracking.
      </Paragraph>
      <Paragraph type="secondary">
        This page will include:
        <ul>
          <li>Contact list with search and filters</li>
          <li>Custom field columns (configurable)</li>
          <li>Contact detail view with message history</li>
          <li>Sentiment timeline per contact</li>
          <li>Bulk import/export functionality</li>
          <li>Tag management</li>
        </ul>
      </Paragraph>
    </div>
  );
}
