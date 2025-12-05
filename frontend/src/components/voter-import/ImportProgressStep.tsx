import { Typography, Card, Statistic, Row, Col, Table, Result, Alert } from 'antd';
import {
  PlusOutlined,
  SyncOutlined,
  MinusCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import type { JobProgress, Job } from '../../services/voterImportService';

const { Text, Paragraph } = Typography;

interface ImportProgressStepProps {
  job: Job;
  progress: JobProgress | null;
}

export default function ImportProgressStep({ job, progress }: ImportProgressStepProps) {
  const isQueued = job.status === 'queued';
  const isProcessing = job.status === 'processing';
  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';

  const currentProgress = progress || {
    status: job.status,
    rows_processed: job.rows_processed,
    rows_created: job.rows_created,
    rows_updated: job.rows_updated,
    rows_skipped: job.rows_skipped,
    rows_errored: job.rows_errored,
    total_rows: job.total_rows,
    percent_complete: job.total_rows
      ? (job.rows_processed / job.total_rows) * 100
      : 0,
  };

  // For queued jobs, show a simple confirmation
  if (isQueued || (job.status !== 'completed' && job.status !== 'failed' && !isProcessing)) {
    return (
      <Result
        icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
        title="Import Submitted"
        subTitle={
          <>
            Your import of <strong>{job.original_filename}</strong> with {job.total_rows?.toLocaleString() || 'N/A'} rows has been queued for processing.
          </>
        }
        extra={
          <Alert
            message="Track Progress"
            description={
              <>
                You can monitor the import status on the <Link to="/jobs">Jobs page</Link>.
                The import will continue processing in the background.
              </>
            }
            type="info"
            showIcon
            style={{ textAlign: 'left', maxWidth: 500, margin: '0 auto' }}
          />
        }
      />
    );
  }

  const getStatusDisplay = () => {
    if (isCompleted) {
      return (
        <Result
          status="success"
          title="Import Complete"
          subTitle={`Successfully processed ${currentProgress.rows_processed} records`}
        />
      );
    }

    if (isFailed) {
      return (
        <Result
          status="error"
          title="Import Failed"
          subTitle={job.error_message || 'An error occurred during import'}
        />
      );
    }

    // Processing state (shouldn't normally show since we redirect to Jobs)
    return (
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <SyncOutlined spin style={{ fontSize: 48, color: '#1890ff' }} />
        <Paragraph style={{ marginTop: 16 }}>Processing...</Paragraph>
      </div>
    );
  };

  const errorColumns = [
    {
      title: 'Row',
      dataIndex: 'row',
      key: 'row',
      width: 80,
    },
    {
      title: 'Error',
      dataIndex: 'error',
      key: 'error',
    },
  ];

  return (
    <div>
      {getStatusDisplay()}

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Created"
              value={currentProgress.rows_created}
              prefix={<PlusOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Updated"
              value={currentProgress.rows_updated}
              prefix={<SyncOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Skipped"
              value={currentProgress.rows_skipped}
              prefix={<MinusCircleOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Errors"
              value={currentProgress.rows_errored}
              prefix={<WarningOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {isCompleted && (
        <Alert
          message="Next Steps"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>Review imported contacts in the Contacts section</li>
              <li>Check vote history on individual contact records</li>
              <li>Run any workflows or campaigns on the new/updated contacts</li>
            </ul>
          }
          type="info"
          showIcon
          style={{ marginTop: 24 }}
        />
      )}

      {job.error_details && job.error_details.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <Text strong>Errors ({job.error_details.length}):</Text>
          <Table
            dataSource={job.error_details.map((e, i) => ({ ...e, key: i }))}
            columns={errorColumns}
            size="small"
            pagination={{ pageSize: 5 }}
            style={{ marginTop: 8 }}
          />
        </div>
      )}

      {isCompleted && (
        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Text type="secondary">
            Completed at {job.completed_at ? new Date(job.completed_at).toLocaleString() : 'N/A'}
          </Text>
        </div>
      )}
    </div>
  );
}
