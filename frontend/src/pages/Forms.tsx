import { Typography } from 'antd';

const { Title, Paragraph } = Typography;

export default function Forms() {
  return (
    <div>
      <Title level={2}>Forms</Title>
      <Paragraph>
        Form builder for surveys and data collection.
      </Paragraph>
      <Paragraph type="secondary">
        This page will include:
        <ul>
          <li>Form list with publish status</li>
          <li>Drag-and-drop form builder</li>
          <li>Field type library</li>
          <li>Conditional logic builder</li>
          <li>Theme/styling options</li>
          <li>Embed code generator</li>
          <li>Submission analytics</li>
        </ul>
      </Paragraph>
    </div>
  );
}
