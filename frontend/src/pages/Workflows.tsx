import { Typography } from 'antd';

const { Title, Paragraph } = Typography;

export default function Workflows() {
  return (
    <div>
      <Title level={2}>Workflows</Title>
      <Paragraph>
        Automation rules for message processing.
      </Paragraph>
      <Paragraph type="secondary">
        This page will include:
        <ul>
          <li>Workflow list with active/inactive status</li>
          <li>Visual workflow builder</li>
          <li>Trigger condition configuration</li>
          <li>Action configuration (auto-reply, assign, notify, webhook)</li>
          <li>Workflow testing interface</li>
          <li>Execution history and logs</li>
        </ul>
      </Paragraph>
    </div>
  );
}
