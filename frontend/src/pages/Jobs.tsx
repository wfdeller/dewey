import { useState } from 'react';
import {
  Typography,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Descriptions,
  Statistic,
  Row,
  Col,
  Card,
  Alert,
  Tooltip,
  App,
} from 'antd';
import {
  ReloadOutlined,
  EyeOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useJobsQuery, useDeleteJobMutation, Job, ErrorDetail } from '../services/voterImportService';
import { getErrorMessage } from '../services/api';

const { Title, Text } = Typography;

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, label: 'Pending' },
  analyzing: { color: 'processing', icon: <SyncOutlined spin />, label: 'Analyzing' },
  mapping: { color: 'warning', icon: <ClockCircleOutlined />, label: 'Awaiting Confirmation' },
  queued: { color: 'processing', icon: <ClockCircleOutlined />, label: 'Queued' },
  processing: { color: 'processing', icon: <SyncOutlined spin />, label: 'Processing' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, label: 'Completed' },
  failed: { color: 'error', icon: <CloseCircleOutlined />, label: 'Failed' },
  stale: { color: 'warning', icon: <ExclamationCircleOutlined />, label: 'Stale' },
};

// Jobs not updated in 10 minutes that are still "processing" are likely stale
const STALE_THRESHOLD_MS = 10 * 60 * 1000;

const isJobStale = (job: Job): boolean => {
  if (job.status !== 'processing') return false;
  const updatedAt = new Date(job.updated_at).getTime();
  const now = Date.now();
  return (now - updatedAt) > STALE_THRESHOLD_MS;
};

const getEffectiveStatus = (job: Job): string => {
  if (isJobStale(job)) return 'stale';
  return job.status;
};

export default function Jobs() {
  const { message, modal } = App.useApp();
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);

  const { data: jobsData, isLoading, refetch } = useJobsQuery(50, 0);
  const deleteMutation = useDeleteJobMutation();

  const handleViewDetails = (job: Job) => {
    setSelectedJob(job);
    setDetailsModalOpen(true);
  };

  const handleDelete = (job: Job) => {
    modal.confirm({
      title: 'Delete Job',
      content: `Are you sure you want to delete this job "${job.original_filename || job.id}"?`,
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        try {
          await deleteMutation.mutateAsync(job.id);
          message.success('Job deleted');
        } catch (error) {
          message.error(getErrorMessage(error));
        }
      },
    });
  };

  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  const formatDuration = (start: string | null, end: string | null, status: string) => {
    if (!start) return '-';
    // For incomplete jobs, don't show running duration - just show "-"
    if (!end && (status === 'processing' || status === 'analyzing' || status === 'pending' || status === 'mapping')) {
      return '-';
    }
    if (!end) return '-';
    const startDate = new Date(start);
    const endDate = new Date(end);
    const diffMs = endDate.getTime() - startDate.getTime();
    if (diffMs < 0) return '-'; // Handle edge case of bad data
    const diffSecs = Math.floor(diffMs / 1000);
    if (diffSecs < 60) return `${diffSecs}s`;
    const mins = Math.floor(diffSecs / 60);
    const secs = diffSecs % 60;
    return `${mins}m ${secs}s`;
  };

  const columns: ColumnsType<Job> = [
    {
      title: 'File',
      dataIndex: 'original_filename',
      key: 'filename',
      render: (filename: string | null, record: Job) => (
        <Tooltip title={record.id}>
          <Text>{filename || 'Unknown'}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 150,
      render: (_: string, record: Job) => {
        const effectiveStatus = getEffectiveStatus(record);
        const config = STATUS_CONFIG[effectiveStatus] || STATUS_CONFIG.pending;
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.label}
          </Tag>
        );
      },
    },
    {
      title: 'Results',
      key: 'results',
      width: 140,
      render: (_: unknown, record: Job) => (
        <Space size={4}>
          <Tooltip title="Created"><Tag color="green" style={{ margin: 0 }}>{record.rows_created}</Tag></Tooltip>
          <Tooltip title="Updated"><Tag color="blue" style={{ margin: 0 }}>{record.rows_updated}</Tag></Tooltip>
          <Tooltip title="Skipped"><Tag style={{ margin: 0 }}>{record.rows_skipped}</Tag></Tooltip>
          <Tooltip title="Errors"><Tag color={record.rows_errored > 0 ? 'red' : undefined} style={{ margin: 0 }}>{record.rows_errored}</Tag></Tooltip>
        </Space>
      ),
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 160,
      render: (date: string | null) => formatDateTime(date),
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 100,
      render: (_: unknown, record: Job) => formatDuration(record.started_at, record.completed_at, record.status),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: Job) => (
        <Space>
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetails(record)}
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              disabled={record.status === 'processing' || record.status === 'analyzing'}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={2} style={{ marginBottom: 0 }}>Jobs</Title>
          <Text type="secondary">View import job history and execution details</Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          Refresh
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={jobsData?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          total: jobsData?.total || 0,
          pageSize: 50,
          showTotal: (total) => `${total} jobs`,
        }}
      />

      <Modal
        title="Job Details"
        open={detailsModalOpen}
        onCancel={() => setDetailsModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailsModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {selectedJob && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="Created"
                    value={selectedJob.rows_created}
                    valueStyle={{ color: '#52c41a' }}
                    prefix={<CheckCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="Updated"
                    value={selectedJob.rows_updated}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="Skipped"
                    value={selectedJob.rows_skipped}
                    valueStyle={{ color: '#8c8c8c' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="Errors"
                    value={selectedJob.rows_errored}
                    valueStyle={{ color: selectedJob.rows_errored > 0 ? '#ff4d4f' : '#8c8c8c' }}
                    prefix={selectedJob.rows_errored > 0 ? <ExclamationCircleOutlined /> : undefined}
                  />
                </Card>
              </Col>
            </Row>

            <Descriptions
              bordered
              column={2}
              size="small"
              style={{ marginTop: 16 }}
            >
              <Descriptions.Item label="Job ID" span={2}>
                <Text copyable style={{ fontFamily: 'monospace' }}>{selectedJob.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="File Name">
                {selectedJob.original_filename || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="File Size">
                {selectedJob.file_size_bytes
                  ? `${(selectedJob.file_size_bytes / 1024).toFixed(1)} KB`
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={STATUS_CONFIG[getEffectiveStatus(selectedJob)]?.color}>
                  {STATUS_CONFIG[getEffectiveStatus(selectedJob)]?.label || selectedJob.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Total Rows">
                {selectedJob.total_rows?.toLocaleString() || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Matching Strategy">
                {selectedJob.matching_strategy || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Create Unmatched">
                {selectedJob.create_unmatched ? 'Yes' : 'No'}
              </Descriptions.Item>
              <Descriptions.Item label="Started">
                {formatDateTime(selectedJob.started_at)}
              </Descriptions.Item>
              <Descriptions.Item label="Completed">
                {formatDateTime(selectedJob.completed_at)}
              </Descriptions.Item>
              <Descriptions.Item label="Duration" span={2}>
                {formatDuration(selectedJob.started_at, selectedJob.completed_at, selectedJob.status)}
              </Descriptions.Item>
              <Descriptions.Item label="Created At">
                {formatDateTime(selectedJob.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="Job Type">
                {selectedJob.job_type}
              </Descriptions.Item>
            </Descriptions>

            {selectedJob.error_message && (
              <Alert
                message="Error"
                description={selectedJob.error_message}
                type="error"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}

            {selectedJob.error_details && selectedJob.error_details.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Title level={5}>Error Details ({selectedJob.error_details.length} errors)</Title>
                <Table
                  dataSource={selectedJob.error_details.slice(0, 100)}
                  rowKey={(record: ErrorDetail) => `${record.row}-${record.error}`}
                  size="small"
                  pagination={{ pageSize: 10 }}
                  columns={[
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
                    {
                      title: 'Data',
                      dataIndex: 'data',
                      key: 'data',
                      render: (data: Record<string, string> | undefined) =>
                        data ? (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {JSON.stringify(data).slice(0, 100)}...
                          </Text>
                        ) : (
                          '-'
                        ),
                    },
                  ]}
                />
                {selectedJob.error_details.length > 100 && (
                  <Text type="secondary">
                    Showing first 100 of {selectedJob.error_details.length} errors
                  </Text>
                )}
              </div>
            )}

            {selectedJob.rows_skipped > 0 && (
              <Alert
                message={`${selectedJob.rows_skipped} rows were skipped`}
                description={
                  selectedJob.create_unmatched
                    ? 'Rows may have been skipped due to missing identifying information (no email, name, or voter ID).'
                    : 'Rows were skipped because they did not match existing contacts and "Create new contacts" was disabled.'
                }
                type="info"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
