import { Typography } from 'antd';

const { Title, Paragraph } = Typography;

export default function Categories() {
  return (
    <div>
      <Title level={2}>Categories</Title>
      <Paragraph>
        Hierarchical category management for message classification.
      </Paragraph>
      <Paragraph type="secondary">
        This page will include:
        <ul>
          <li>Tree view of categories with drag-and-drop</li>
          <li>Add/edit category modal</li>
          <li>Color picker for category colors</li>
          <li>Keyword configuration for auto-matching</li>
          <li>Category usage statistics</li>
        </ul>
      </Paragraph>
    </div>
  );
}
