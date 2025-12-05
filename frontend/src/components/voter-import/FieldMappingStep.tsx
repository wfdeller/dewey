import { Table, Select, Tag, Typography, Space, Tooltip } from 'antd';
import { CheckCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { FieldMapping, getGroupedFieldOptions } from '../../services/voterImportService';

const { Text } = Typography;

interface MappingRow {
  key: string;
  header: string;
  suggestedField: string | null;
  confidence: number;
  reason: string;
  selectedField: string | null;
  isVoteHistory: boolean;
}

interface FieldMappingStepProps {
  headers: string[];
  suggestedMappings: Record<string, FieldMapping>;
  voteHistoryColumns: string[];
  confirmedMappings: Record<string, string | null>;
  onMappingChange: (header: string, field: string | null) => void;
}

export default function FieldMappingStep({
  headers,
  suggestedMappings,
  voteHistoryColumns,
  confirmedMappings,
  onMappingChange,
}: FieldMappingStepProps) {
  const fieldOptions = getGroupedFieldOptions();

  // Add a "Skip this column" option
  const selectOptions = [
    { value: '', label: '-- Skip this column --' },
    ...fieldOptions,
  ];

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'green';
    if (confidence >= 0.7) return 'blue';
    if (confidence >= 0.5) return 'orange';
    return 'default';
  };

  const data: MappingRow[] = headers.map((header) => {
    const mapping = suggestedMappings[header];
    const isVoteHistory = voteHistoryColumns.includes(header);

    return {
      key: header,
      header,
      suggestedField: mapping?.field || null,
      confidence: mapping?.confidence || 0,
      reason: mapping?.reason || '',
      selectedField: confirmedMappings[header] ?? mapping?.field ?? null,
      isVoteHistory,
    };
  });

  const columns: ColumnsType<MappingRow> = [
    {
      title: 'CSV Column',
      dataIndex: 'header',
      key: 'header',
      width: '25%',
      render: (header: string, row: MappingRow) => (
        <Space>
          <Text code>{header}</Text>
          {row.isVoteHistory && (
            <Tag color="purple" icon={<CheckCircleOutlined />}>
              Vote History
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'AI Suggestion',
      key: 'suggestion',
      width: '25%',
      render: (_, row: MappingRow) => {
        if (!row.suggestedField) {
          return <Text type="secondary">No match found</Text>;
        }
        return (
          <Space>
            <Tag color={getConfidenceColor(row.confidence)}>
              {row.suggestedField}
            </Tag>
            <Tooltip title={row.reason}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {Math.round(row.confidence * 100)}%
                <QuestionCircleOutlined style={{ marginLeft: 4 }} />
              </Text>
            </Tooltip>
          </Space>
        );
      },
    },
    {
      title: 'Map To',
      key: 'mapping',
      width: '50%',
      render: (_, row: MappingRow) => (
        <Select
          style={{ width: '100%' }}
          value={row.selectedField || ''}
          onChange={(value) => onMappingChange(row.header, value || null)}
          options={selectOptions}
          placeholder="Select a field..."
          showSearch
          filterOption={(input, option) =>
            (option?.label?.toString() || '').toLowerCase().includes(input.toLowerCase())
          }
        />
      ),
    },
  ];

  // Count mapped vs unmapped
  const mappedCount = Object.values(confirmedMappings).filter((v) => v).length;
  const totalCount = headers.length;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Text>
          Review and confirm the field mappings below. The AI has suggested mappings based on column names.
        </Text>
        <div style={{ marginTop: 8 }}>
          <Tag color={mappedCount === totalCount ? 'green' : 'blue'}>
            {mappedCount} of {totalCount} columns mapped
          </Tag>
          {voteHistoryColumns.length > 0 && (
            <Tag color="purple">
              {voteHistoryColumns.length} vote history column{voteHistoryColumns.length > 1 ? 's' : ''} detected
            </Tag>
          )}
        </div>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        pagination={false}
        size="small"
        scroll={{ y: 400 }}
      />
    </div>
  );
}
