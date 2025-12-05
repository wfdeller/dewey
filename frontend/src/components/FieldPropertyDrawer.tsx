import { useEffect } from 'react';
import {
  Drawer,
  Form,
  Input,
  Switch,
  Button,
  Space,
  Divider,
  InputNumber,
  Select,
  Typography,
} from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { FormField, FormFieldType } from '../types';

const { Text } = Typography;

interface FieldPropertyDrawerProps {
  open: boolean;
  field: FormField | null;
  onClose: () => void;
  onSave: (fieldId: string, data: Partial<FormField>) => void;
  loading?: boolean;
}

// Field types that support options
const OPTION_FIELD_TYPES: FormFieldType[] = ['select', 'multi_select', 'radio', 'checkbox'];

export default function FieldPropertyDrawer({
  open,
  field,
  onClose,
  onSave,
  loading,
}: FieldPropertyDrawerProps) {
  const [form] = Form.useForm();

  // Reset form when field changes
  useEffect(() => {
    if (field) {
      form.setFieldsValue({
        label: field.label,
        placeholder: field.placeholder || '',
        help_text: field.help_text || '',
        is_required: field.is_required,
        options: field.options || [],
        validation: field.validation || {},
      });
    } else {
      form.resetFields();
    }
  }, [field, form]);

  const handleSubmit = async () => {
    if (!field) return;

    try {
      const values = await form.validateFields();
      onSave(field.id, values);
    } catch {
      // Validation failed
    }
  };

  const showOptions = field && OPTION_FIELD_TYPES.includes(field.field_type);

  return (
    <Drawer
      title={field ? `Edit: ${field.label}` : 'Edit Field'}
      open={open}
      onClose={onClose}
      width={400}
      extra={
        <Space>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="primary" onClick={handleSubmit} loading={loading}>
            Save
          </Button>
        </Space>
      }
    >
      {field && (
        <Form form={form} layout="vertical">
          {/* Basic properties */}
          <Form.Item
            name="label"
            label="Label"
            rules={[{ required: true, message: 'Label is required' }]}
          >
            <Input placeholder="Enter field label" />
          </Form.Item>

          <Form.Item name="placeholder" label="Placeholder">
            <Input placeholder="Enter placeholder text" />
          </Form.Item>

          <Form.Item name="help_text" label="Help Text">
            <Input.TextArea
              rows={2}
              placeholder="Additional instructions for the user"
            />
          </Form.Item>

          <Form.Item name="is_required" label="Required" valuePropName="checked">
            <Switch />
          </Form.Item>

          {/* Options for select/radio/checkbox fields */}
          {showOptions && (
            <>
              <Divider>Options</Divider>
              <Form.List name="options">
                {(fields, { add, remove }) => (
                  <>
                    {fields.map(({ key, name, ...restField }) => (
                      <div
                        key={key}
                        style={{
                          display: 'flex',
                          gap: 8,
                          marginBottom: 8,
                          alignItems: 'flex-start',
                        }}
                      >
                        <Form.Item
                          {...restField}
                          name={[name, 'value']}
                          style={{ flex: 1, marginBottom: 0 }}
                          rules={[{ required: true, message: 'Value required' }]}
                        >
                          <Input placeholder="Value" />
                        </Form.Item>
                        <Form.Item
                          {...restField}
                          name={[name, 'label']}
                          style={{ flex: 1, marginBottom: 0 }}
                          rules={[{ required: true, message: 'Label required' }]}
                        >
                          <Input placeholder="Display Label" />
                        </Form.Item>
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(name)}
                        />
                      </div>
                    ))}
                    <Button
                      type="dashed"
                      onClick={() => add({ value: '', label: '' })}
                      block
                      icon={<PlusOutlined />}
                    >
                      Add Option
                    </Button>
                  </>
                )}
              </Form.List>
            </>
          )}

          {/* Validation rules based on field type */}
          <Divider>Validation</Divider>

          {field.field_type === 'text' && (
            <>
              <Form.Item name={['validation', 'minLength']} label="Min Length">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name={['validation', 'maxLength']} label="Max Length">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name={['validation', 'pattern']} label="Pattern (Regex)">
                <Input placeholder="e.g., ^[A-Za-z]+$" />
              </Form.Item>
            </>
          )}

          {field.field_type === 'textarea' && (
            <>
              <Form.Item name={['validation', 'minLength']} label="Min Length">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name={['validation', 'maxLength']} label="Max Length">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}

          {field.field_type === 'number' && (
            <>
              <Form.Item name={['validation', 'min']} label="Min Value">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name={['validation', 'max']} label="Max Value">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}

          {field.field_type === 'file_upload' && (
            <>
              <Form.Item name={['validation', 'maxSize']} label="Max File Size (MB)">
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name={['validation', 'allowedTypes']} label="Allowed File Types">
                <Select
                  mode="multiple"
                  placeholder="Select allowed types"
                  options={[
                    { value: 'image/*', label: 'Images' },
                    { value: 'application/pdf', label: 'PDF' },
                    { value: '.doc,.docx', label: 'Word Documents' },
                    { value: '.xls,.xlsx', label: 'Excel Files' },
                  ]}
                />
              </Form.Item>
            </>
          )}

          {/* Contact field mapping */}
          <Divider>Contact Mapping</Divider>
          <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
            Map this field to automatically populate contact information
          </Text>
          <Form.Item name="mapsToContactField" label="Maps to Contact Field">
            <Select
              allowClear
              placeholder="Select contact field"
              options={[
                { value: 'email', label: 'Email' },
                { value: 'name', label: 'Name' },
                { value: 'phone', label: 'Phone' },
              ]}
            />
          </Form.Item>
        </Form>
      )}
    </Drawer>
  );
}
