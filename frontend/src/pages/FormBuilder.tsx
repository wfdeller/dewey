import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Button, Space, Card, Tabs, Empty, Spin, message, Tooltip, Tag } from 'antd';
import {
    ArrowLeftOutlined,
    SaveOutlined,
    EyeOutlined,
    DeleteOutlined,
    HolderOutlined,
    SettingOutlined,
    CopyOutlined,
    EditOutlined,
    CheckCircleOutlined,
} from '@ant-design/icons';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent,
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    useSortable,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { FormField, FormFieldType } from '../types';
import {
    useFormQuery,
    useAddFieldMutation,
    useUpdateFieldMutation,
    useDeleteFieldMutation,
    useReorderFieldsMutation,
    useUpdateFormMutation,
} from '../services/formsService';
import { getErrorMessage } from '../services/api';
import FieldPropertyDrawer from '../components/FieldPropertyDrawer';
import FormPreview from '../components/FormPreview';

const { Title, Text } = Typography;

// Field type configuration
const FIELD_TYPES: { type: FormFieldType; label: string; icon: string; description: string }[] = [
    { type: 'text', label: 'Text', icon: 'Aa', description: 'Single line text input' },
    { type: 'textarea', label: 'Text Area', icon: '=', description: 'Multi-line text input' },
    { type: 'email', label: 'Email', icon: '@', description: 'Email address input' },
    { type: 'phone', label: 'Phone', icon: '#', description: 'Phone number input' },
    { type: 'number', label: 'Number', icon: '123', description: 'Numeric input' },
    { type: 'date', label: 'Date', icon: 'D', description: 'Date picker' },
    { type: 'select', label: 'Dropdown', icon: 'V', description: 'Single selection dropdown' },
    { type: 'multi_select', label: 'Multi-Select', icon: 'M', description: 'Multiple selection' },
    { type: 'radio', label: 'Radio', icon: 'O', description: 'Single choice radio buttons' },
    { type: 'checkbox', label: 'Checkboxes', icon: '[]', description: 'Multiple choice checkboxes' },
    { type: 'rating', label: 'Rating', icon: '*', description: '5-star rating' },
    { type: 'nps', label: 'NPS', icon: '0-10', description: 'Net Promoter Score (0-10)' },
    { type: 'file_upload', label: 'File Upload', icon: 'F', description: 'File attachment' },
    { type: 'hidden', label: 'Hidden', icon: 'H', description: 'Hidden field for tracking' },
];

// Sortable field card component
interface SortableFieldCardProps {
    field: FormField;
    onEdit: () => void;
    onDelete: () => void;
    onDuplicate: () => void;
}

function SortableFieldCard({ field, onEdit, onDelete, onDuplicate }: SortableFieldCardProps) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: field.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    const fieldTypeConfig = FIELD_TYPES.find((t) => t.type === field.field_type);

    return (
        <div ref={setNodeRef} style={style}>
            <Card
                size='small'
                style={{ marginBottom: 8, cursor: 'default' }}
                styles={{ body: { padding: '12px 16px' } }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div
                        {...attributes}
                        {...listeners}
                        style={{ cursor: 'grab', color: '#999', display: 'flex', alignItems: 'center' }}
                    >
                        <HolderOutlined style={{ fontSize: 16 }} />
                    </div>

                    <div
                        style={{
                            width: 36,
                            height: 36,
                            background: '#f0f0f0',
                            borderRadius: 4,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 500,
                            fontSize: 12,
                            color: '#666',
                        }}
                    >
                        {fieldTypeConfig?.icon || '?'}
                    </div>

                    <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <Text strong>{field.label}</Text>
                            {field.is_required && (
                                <Tag color='red' style={{ fontSize: 10 }}>
                                    Required
                                </Tag>
                            )}
                        </div>
                        <Text type='secondary' style={{ fontSize: 12 }}>
                            {fieldTypeConfig?.label || field.field_type}
                        </Text>
                    </div>

                    <Space size='small'>
                        <Tooltip title='Edit'>
                            <Button size='small' icon={<EditOutlined />} onClick={onEdit} />
                        </Tooltip>
                        <Tooltip title='Duplicate'>
                            <Button size='small' icon={<CopyOutlined />} onClick={onDuplicate} />
                        </Tooltip>
                        <Tooltip title='Delete'>
                            <Button size='small' danger icon={<DeleteOutlined />} onClick={onDelete} />
                        </Tooltip>
                    </Space>
                </div>
            </Card>
        </div>
    );
}

export default function FormBuilder() {
    const { formId } = useParams<{ formId: string }>();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('edit');
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [editingField, setEditingField] = useState<FormField | null>(null);
    const [localFields, setLocalFields] = useState<FormField[]>([]);
    const [hasUnsavedReorder, setHasUnsavedReorder] = useState(false);

    const { data: form, isLoading, refetch } = useFormQuery(formId || '');
    const addFieldMutation = useAddFieldMutation();
    const updateFieldMutation = useUpdateFieldMutation();
    const deleteFieldMutation = useDeleteFieldMutation();
    const reorderFieldsMutation = useReorderFieldsMutation();
    const updateFormMutation = useUpdateFormMutation();

    // Initialize local fields when form data loads
    useEffect(() => {
        if (form?.fields && !hasUnsavedReorder) {
            setLocalFields(form.fields);
        }
    }, [form?.fields, hasUnsavedReorder]);

    // Sync local fields when form data changes (and no unsaved reorder)
    const fields = hasUnsavedReorder ? localFields : form?.fields || [];

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragEnd = useCallback(
        (event: DragEndEvent) => {
            const { active, over } = event;

            if (over && active.id !== over.id) {
                const oldIndex = fields.findIndex((f) => f.id === active.id);
                const newIndex = fields.findIndex((f) => f.id === over.id);
                const newFields = arrayMove(fields, oldIndex, newIndex);
                setLocalFields(newFields);
                setHasUnsavedReorder(true);
            }
        },
        [fields]
    );

    const saveFieldOrder = async () => {
        if (!formId || !hasUnsavedReorder) return;

        try {
            await reorderFieldsMutation.mutateAsync({
                formId,
                fieldOrder: localFields.map((f) => f.id),
            });
            message.success('Field order saved');
            setHasUnsavedReorder(false);
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleAddField = async (fieldType: FormFieldType) => {
        if (!formId) return;

        try {
            await addFieldMutation.mutateAsync({
                formId,
                data: {
                    field_type: fieldType,
                    label: `New ${FIELD_TYPES.find((t) => t.type === fieldType)?.label || 'Field'}`,
                    is_required: false,
                    sort_order: fields.length,
                },
            });
            message.success('Field added');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleEditField = (field: FormField) => {
        setEditingField(field);
        setDrawerOpen(true);
    };

    const handleSaveField = async (fieldId: string, data: Partial<FormField>) => {
        if (!formId) return;

        try {
            await updateFieldMutation.mutateAsync({
                formId,
                fieldId,
                data: {
                    label: data.label,
                    placeholder: data.placeholder,
                    help_text: data.help_text,
                    is_required: data.is_required,
                    validation: data.validation as Record<string, unknown>,
                    options: data.options,
                },
            });
            message.success('Field updated');
            setDrawerOpen(false);
            setEditingField(null);
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleDeleteField = async (fieldId: string) => {
        if (!formId) return;

        try {
            await deleteFieldMutation.mutateAsync({ formId, fieldId });
            message.success('Field deleted');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleDuplicateField = async (field: FormField) => {
        if (!formId) return;

        try {
            await addFieldMutation.mutateAsync({
                formId,
                data: {
                    field_type: field.field_type,
                    label: `${field.label} (Copy)`,
                    placeholder: field.placeholder,
                    help_text: field.help_text,
                    is_required: field.is_required,
                    sort_order: fields.length,
                    validation: field.validation as Record<string, unknown>,
                    options: field.options,
                },
            });
            message.success('Field duplicated');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handlePublish = async () => {
        if (!formId) return;

        try {
            await updateFormMutation.mutateAsync({
                formId,
                data: { status: 'published' },
            });
            message.success('Form published successfully');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    if (isLoading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
                <Spin size='large' />
            </div>
        );
    }

    if (!form) {
        return (
            <Empty description='Form not found'>
                <Button onClick={() => navigate('/forms')}>Back to Forms</Button>
            </Empty>
        );
    }

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space>
                    <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/forms')}>
                        Back
                    </Button>
                    <Title level={3} style={{ margin: 0 }}>
                        {form.name}
                    </Title>
                    <Tag color={form.status === 'published' ? 'green' : 'orange'}>{form.status.toUpperCase()}</Tag>
                </Space>

                <Space>
                    {hasUnsavedReorder && (
                        <Button
                            type='primary'
                            icon={<SaveOutlined />}
                            onClick={saveFieldOrder}
                            loading={reorderFieldsMutation.isPending}
                        >
                            Save Order
                        </Button>
                    )}
                    <Button icon={<EyeOutlined />} onClick={() => setActiveTab('preview')}>
                        Preview
                    </Button>
                    {form.status !== 'published' && (
                        <Button
                            type='primary'
                            icon={<CheckCircleOutlined />}
                            onClick={handlePublish}
                            loading={updateFormMutation.isPending}
                        >
                            Publish
                        </Button>
                    )}
                    <Button icon={<SettingOutlined />} onClick={() => navigate(`/forms/${formId}/settings`)}>
                        Settings
                    </Button>
                </Space>
            </div>

            {/* Main content */}
            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={[
                    {
                        key: 'edit',
                        label: 'Edit Fields',
                        children: (
                            <div style={{ display: 'flex', gap: 24 }}>
                                {/* Field palette */}
                                <Card
                                    title='Add Field'
                                    size='small'
                                    style={{ width: 240, flexShrink: 0 }}
                                    styles={{ body: { padding: 12 } }}
                                >
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                        {FIELD_TYPES.map((fieldType) => (
                                            <Button
                                                key={fieldType.type}
                                                block
                                                style={{ textAlign: 'left', height: 'auto', padding: '8px 12px' }}
                                                onClick={() => handleAddField(fieldType.type)}
                                            >
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                    <div
                                                        style={{
                                                            width: 24,
                                                            height: 24,
                                                            background: '#f0f0f0',
                                                            borderRadius: 4,
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            fontSize: 10,
                                                            fontWeight: 500,
                                                        }}
                                                    >
                                                        {fieldType.icon}
                                                    </div>
                                                    <div>
                                                        <div style={{ fontWeight: 500 }}>{fieldType.label}</div>
                                                        <div style={{ fontSize: 11, color: '#999' }}>
                                                            {fieldType.description}
                                                        </div>
                                                    </div>
                                                </div>
                                            </Button>
                                        ))}
                                    </div>
                                </Card>

                                {/* Form fields */}
                                <Card
                                    title={`Form Fields (${fields.length})`}
                                    style={{ flex: 1 }}
                                    extra={hasUnsavedReorder && <Tag color='orange'>Unsaved changes</Tag>}
                                >
                                    {fields.length === 0 ? (
                                        <Empty description='No fields yet' image={Empty.PRESENTED_IMAGE_SIMPLE}>
                                            <Text type='secondary'>
                                                Click on a field type from the left panel to add it to your form
                                            </Text>
                                        </Empty>
                                    ) : (
                                        <DndContext
                                            sensors={sensors}
                                            collisionDetection={closestCenter}
                                            onDragEnd={handleDragEnd}
                                        >
                                            <SortableContext
                                                items={fields.map((f) => f.id)}
                                                strategy={verticalListSortingStrategy}
                                            >
                                                {fields.map((field) => (
                                                    <SortableFieldCard
                                                        key={field.id}
                                                        field={field}
                                                        onEdit={() => handleEditField(field)}
                                                        onDelete={() => handleDeleteField(field.id)}
                                                        onDuplicate={() => handleDuplicateField(field)}
                                                    />
                                                ))}
                                            </SortableContext>
                                        </DndContext>
                                    )}
                                </Card>
                            </div>
                        ),
                    },
                    {
                        key: 'preview',
                        label: 'Preview',
                        children: <FormPreview form={form} fields={fields} />,
                    },
                ]}
            />

            {/* Field property drawer */}
            <FieldPropertyDrawer
                open={drawerOpen}
                field={editingField}
                onClose={() => {
                    setDrawerOpen(false);
                    setEditingField(null);
                }}
                onSave={handleSaveField}
                loading={updateFieldMutation.isPending}
            />
        </div>
    );
}
