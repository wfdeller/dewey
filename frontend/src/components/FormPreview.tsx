import {
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  Rate,
  Upload,
  Button,
  Radio,
  Checkbox,
  Card,
  Typography,
  Space,
} from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { Form as FormType, FormField } from '../types';

const { Title, Paragraph } = Typography;

interface FormPreviewProps {
  form: FormType;
  fields: FormField[];
  onSubmit?: (values: Record<string, unknown>) => void;
  isEmbedded?: boolean;
}

// Render a single field based on its type
function renderField(field: FormField) {
  const commonProps = {
    placeholder: field.placeholder,
  };

  switch (field.field_type) {
    case 'text':
      return <Input {...commonProps} />;

    case 'textarea':
      return <Input.TextArea {...commonProps} rows={4} />;

    case 'email':
      return <Input {...commonProps} type="email" />;

    case 'phone':
      return <Input {...commonProps} type="tel" />;

    case 'number':
      return (
        <InputNumber
          {...commonProps}
          style={{ width: '100%' }}
          min={field.validation?.min as number}
          max={field.validation?.max as number}
        />
      );

    case 'date':
      return <DatePicker {...commonProps} style={{ width: '100%' }} />;

    case 'select':
      return (
        <Select
          {...commonProps}
          options={field.options?.map((opt) => ({
            value: opt.value,
            label: opt.label,
          }))}
        />
      );

    case 'multi_select':
      return (
        <Select
          {...commonProps}
          mode="multiple"
          options={field.options?.map((opt) => ({
            value: opt.value,
            label: opt.label,
          }))}
        />
      );

    case 'radio':
      return (
        <Radio.Group>
          <Space direction="vertical">
            {field.options?.map((opt) => (
              <Radio key={opt.value} value={opt.value}>
                {opt.label}
              </Radio>
            ))}
          </Space>
        </Radio.Group>
      );

    case 'checkbox':
      // If no options defined, render as a single checkbox (yes/no style)
      if (!field.options || field.options.length === 0) {
        return <Checkbox>Yes</Checkbox>;
      }
      return (
        <Checkbox.Group>
          <Space direction="vertical">
            {field.options.map((opt) => (
              <Checkbox key={opt.value} value={opt.value}>
                {opt.label}
              </Checkbox>
            ))}
          </Space>
        </Checkbox.Group>
      );

    case 'rating':
      return <Rate />;

    case 'nps':
      return (
        <Radio.Group buttonStyle="solid">
          {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
            <Radio.Button key={n} value={n} style={{ width: 40, textAlign: 'center' }}>
              {n}
            </Radio.Button>
          ))}
        </Radio.Group>
      );

    case 'file_upload':
      return (
        <Upload>
          <Button icon={<UploadOutlined />}>Click to Upload</Button>
        </Upload>
      );

    case 'hidden':
      return <Input type="hidden" />;

    default:
      return <Input {...commonProps} />;
  }
}

export default function FormPreview({
  form: formData,
  fields,
  onSubmit,
  isEmbedded = false,
}: FormPreviewProps) {
  const [form] = Form.useForm();

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      onSubmit?.(values);
    } catch {
      // Validation failed
    }
  };

  const containerStyle = isEmbedded
    ? {}
    : {
        maxWidth: 600,
        margin: '0 auto',
        padding: 24,
      };

  return (
    <div style={containerStyle}>
      <Card
        style={{
          borderRadius: 8,
          ...(formData.styling?.primary_color && {
            borderTop: `4px solid ${formData.styling.primary_color}`,
          }),
        }}
      >
        {/* Form header */}
        <div style={{ marginBottom: 24 }}>
          <Title level={3} style={{ marginBottom: 8 }}>
            {formData.name}
          </Title>
          {formData.description && (
            <Paragraph type="secondary">{formData.description}</Paragraph>
          )}
        </div>

        {/* Form fields */}
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          {fields
            .filter((f) => f.field_type !== 'hidden')
            .map((field) => (
              <Form.Item
                key={field.id}
                name={field.id}
                label={field.label}
                rules={[
                  {
                    required: field.is_required,
                    message: `${field.label} is required`,
                  },
                  // Email validation
                  ...(field.field_type === 'email'
                    ? [{ type: 'email' as const, message: 'Please enter a valid email' }]
                    : []),
                  // Min/max length validation
                  ...(field.validation?.minLength
                    ? [
                        {
                          min: field.validation.minLength as number,
                          message: `Minimum ${field.validation.minLength} characters`,
                        },
                      ]
                    : []),
                  ...(field.validation?.maxLength
                    ? [
                        {
                          max: field.validation.maxLength as number,
                          message: `Maximum ${field.validation.maxLength} characters`,
                        },
                      ]
                    : []),
                  // Pattern validation
                  ...(field.validation?.pattern
                    ? [
                        {
                          pattern: new RegExp(field.validation.pattern as string),
                          message: 'Invalid format',
                        },
                      ]
                    : []),
                ]}
                extra={field.help_text}
              >
                {renderField(field)}
              </Form.Item>
            ))}

          {/* Hidden fields */}
          {fields
            .filter((f) => f.field_type === 'hidden')
            .map((field) => (
              <Form.Item key={field.id} name={field.id} hidden>
                <Input type="hidden" />
              </Form.Item>
            ))}

          {/* Submit button */}
          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              block
              size="large"
              style={
                formData.styling?.primary_color
                  ? { backgroundColor: formData.styling.primary_color }
                  : undefined
              }
            >
              {formData.settings?.submit_button_text || 'Submit'}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
