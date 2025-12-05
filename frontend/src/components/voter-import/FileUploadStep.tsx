import { Upload, Typography, Alert } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';

const { Dragger } = Upload;
const { Text, Paragraph } = Typography;

interface FileUploadStepProps {
  onFileSelect: (file: File) => void;
  isLoading: boolean;
  error: string | null;
}

export default function FileUploadStep({ onFileSelect, isLoading, error }: FileUploadStepProps) {
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.csv',
    maxCount: 1,
    beforeUpload: (file) => {
      onFileSelect(file);
      return false; // Prevent automatic upload
    },
    showUploadList: false,
    disabled: isLoading,
  };

  return (
    <div style={{ padding: '24px 0' }}>
      {error && (
        <Alert
          message="Upload Error"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      <Dragger {...uploadProps} style={{ padding: 24 }}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined style={{ fontSize: 48, color: '#1890ff' }} />
        </p>
        <p className="ant-upload-text">Click or drag a CSV file to upload</p>
        <p className="ant-upload-hint">
          Upload a voter file in CSV format. The file will be analyzed and you can map columns to contact fields.
        </p>
      </Dragger>

      <div style={{ marginTop: 24 }}>
        <Text strong>Supported formats:</Text>
        <Paragraph type="secondary" style={{ marginTop: 8 }}>
          - CSV files up to 50MB
          <br />
          - UTF-8 encoding recommended
          <br />
          - First row should contain column headers
        </Paragraph>

        <Text strong style={{ marginTop: 16, display: 'block' }}>
          Common voter file columns:
        </Text>
        <Paragraph type="secondary" style={{ marginTop: 8 }}>
          - Voter ID, First Name, Last Name, Email, Phone
          <br />
          - Address, City, State, ZIP, County, Precinct
          <br />
          - Party Affiliation, Voter Status, Registration Date
          <br />
          - Vote history columns (e.g., 2024_gen, 2022_pri)
        </Paragraph>
      </div>
    </div>
  );
}
