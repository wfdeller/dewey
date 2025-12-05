import { Radio, Typography, Card, Tag, Space, Alert, Checkbox, Divider } from 'antd';
import { BulbOutlined, CheckCircleOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

interface MatchingStrategyStepProps {
  strategies: Record<string, string>;
  suggestedStrategy: string;
  suggestedReason: string;
  selectedStrategy: string;
  onStrategyChange: (strategy: string) => void;
  createUnmatched: boolean;
  onCreateUnmatchedChange: (value: boolean) => void;
}

export default function MatchingStrategyStep({
  strategies,
  suggestedStrategy,
  suggestedReason,
  selectedStrategy,
  onStrategyChange,
  createUnmatched,
  onCreateUnmatchedChange,
}: MatchingStrategyStepProps) {
  const strategyDescriptions: Record<string, { title: string; description: string }> = {
    voter_id_first: {
      title: 'Voter ID First',
      description:
        'Best for official voter files. Matches contacts by State Voter ID first, then falls back to email if no match found.',
    },
    email_first: {
      title: 'Email First',
      description:
        'Best for contact lists with good email coverage. Matches by email first, then falls back to Voter ID.',
    },
    voter_id_only: {
      title: 'Voter ID Only',
      description:
        'Strict matching by Voter ID only. Records without a matching Voter ID will be created as new contacts.',
    },
    email_only: {
      title: 'Email Only',
      description:
        'Strict matching by email only. Best for email lists without voter IDs.',
    },
  };

  return (
    <div>
      <Paragraph>
        Choose how to match imported records to existing contacts. The AI has analyzed your file
        and made a recommendation.
      </Paragraph>

      {suggestedStrategy && (
        <Alert
          message={
            <Space>
              <BulbOutlined />
              <Text strong>AI Recommendation: {strategyDescriptions[suggestedStrategy]?.title}</Text>
            </Space>
          }
          description={suggestedReason}
          type="info"
          showIcon={false}
          style={{ marginBottom: 24 }}
        />
      )}

      <Radio.Group
        value={selectedStrategy}
        onChange={(e) => onStrategyChange(e.target.value)}
        style={{ width: '100%' }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {Object.entries(strategies).map(([key]) => {
            const info = strategyDescriptions[key] || {
              title: key,
              description: strategies[key],
            };
            const isRecommended = key === suggestedStrategy;

            return (
              <Card
                key={key}
                size="small"
                style={{
                  cursor: 'pointer',
                  border: selectedStrategy === key ? '2px solid #1890ff' : undefined,
                }}
                onClick={() => onStrategyChange(key)}
              >
                <Radio value={key} style={{ width: '100%' }}>
                  <Space>
                    <Text strong>{info.title}</Text>
                    {isRecommended && (
                      <Tag color="green" icon={<CheckCircleOutlined />}>
                        Recommended
                      </Tag>
                    )}
                  </Space>
                  <Paragraph type="secondary" style={{ marginTop: 4, marginBottom: 0 }}>
                    {info.description}
                  </Paragraph>
                </Radio>
              </Card>
            );
          })}
        </Space>
      </Radio.Group>

      <Divider />

      <div style={{ marginTop: 16 }}>
        <Checkbox
          checked={createUnmatched}
          onChange={(e) => onCreateUnmatchedChange(e.target.checked)}
        >
          <Text strong>Create new contacts if no match is found</Text>
        </Checkbox>
        <Paragraph type="secondary" style={{ marginTop: 8, marginLeft: 24 }}>
          When enabled, records that don't match any existing contact will be imported as new contacts.
          When disabled, only existing contacts will be updated and unmatched records will be skipped.
        </Paragraph>
      </div>
    </div>
  );
}
