import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Typography,
    Card,
    Descriptions,
    Table,
    Tag,
    Space,
    Button,
    Spin,
    Empty,
    Row,
    Col,
    Statistic,
    Form,
    Input,
    Modal,
    Popconfirm,
    Tabs,
    Select,
    DatePicker,
    InputNumber,
    Switch,
    Alert,
    App,
} from 'antd';
import {
    ArrowLeftOutlined,
    MailOutlined,
    TagOutlined,
    EditOutlined,
    DeleteOutlined,
    PlusOutlined,
    CloseOutlined,
    UserOutlined,
    BankOutlined,
    TeamOutlined,
    IdcardOutlined,
    EnvironmentOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    QuestionCircleOutlined,
    BulbOutlined,
    RobotOutlined,
    HistoryOutlined,
} from '@ant-design/icons';
import { Line } from '@ant-design/charts';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);
import {
    useContactQuery,
    useContactMessagesQuery,
    useContactTimelineQuery,
    useUpdateContactMutation,
    useDeleteContactMutation,
    useAddTagMutation,
    useRemoveTagMutation,
    ContactMessageSummary,
} from '../services/contactsService';
import { useActiveLOVQuery, toSelectOptions } from '../services/lovService';
import {
    useVoteHistoryQuery,
    useVoteSummaryQuery,
    formatVotingMethod,
    formatElectionType,
} from '../services/voteHistoryService';
import { getErrorMessage } from '../services/api';
import { useAuthStore } from '../stores/authStore';
import type { ToneScore } from '../types';

const { Title, Text, Paragraph } = Typography;

// Helper to display value or N/A
const displayValue = (
    value: string | number | boolean | null | undefined,
    formatter?: (v: string | number | boolean) => string
): string => {
    if (value === null || value === undefined || value === '') return 'N/A';
    if (formatter) return formatter(value);
    return String(value);
};

// Format labels for display
const formatLabel = (value: string | undefined): string => {
    if (!value) return 'N/A';
    return value
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
};

// Tone color mapping
const getToneColor = (tone: string): string => {
    const emotionTones: Record<string, string> = {
        angry: 'red',
        frustrated: 'orange',
        grateful: 'green',
        hopeful: 'cyan',
        anxious: 'gold',
        disappointed: 'magenta',
        enthusiastic: 'lime',
        satisfied: 'green',
        confused: 'purple',
        concerned: 'volcano',
    };
    const styleTones: Record<string, string> = {
        cordial: 'blue',
        formal: 'geekblue',
        informal: 'default',
        urgent: 'red',
        demanding: 'volcano',
        polite: 'cyan',
        hostile: 'magenta',
        professional: 'blue',
        casual: 'default',
        apologetic: 'gold',
    };
    return emotionTones[tone] || styleTones[tone] || 'default';
};

// Modal types for editing different sections
type EditModalType = 'contact' | 'demographics' | 'professional' | 'location' | 'voter' | 'status' | null;

// Select options are now loaded from LOV API - see useActiveLOVQuery

export default function ContactDetail() {
    const { contactId } = useParams<{ contactId: string }>();
    const navigate = useNavigate();
    const { message } = App.useApp();
    const hasPermission = useAuthStore((state) => state.hasPermission);
    const canEdit = hasPermission('contacts:write');
    const [messagesPage, setMessagesPage] = useState(1);
    const [messagesPageSize, setMessagesPageSize] = useState(10);
    const [editModal, setEditModal] = useState<EditModalType>(null);
    const [newTag, setNewTag] = useState('');
    const [form] = Form.useForm();

    const { data: contact, isLoading, refetch } = useContactQuery(contactId || '');
    const { data: messagesData, isLoading: messagesLoading } = useContactMessagesQuery(
        contactId || '',
        messagesPage,
        messagesPageSize
    );
    const { data: timelineData } = useContactTimelineQuery(contactId || '', 90);
    const { data: voteHistoryData, isLoading: voteHistoryLoading } = useVoteHistoryQuery(contactId || '');
    const { data: voteSummaryData } = useVoteSummaryQuery(contactId || '');
    const { data: lovData } = useActiveLOVQuery();

    // Convert LOV data to Select options
    const prefixOptions = toSelectOptions(lovData?.prefix);
    const pronounOptions = toSelectOptions(lovData?.pronoun);
    const languageOptions = toSelectOptions(lovData?.language);
    const genderOptions = toSelectOptions(lovData?.gender);
    const maritalStatusOptions = toSelectOptions(lovData?.marital_status);
    const educationOptions = toSelectOptions(lovData?.education_level);
    const incomeOptions = toSelectOptions(lovData?.income_bracket);
    const homeownerOptions = toSelectOptions(lovData?.homeowner_status);
    const voterStatusOptions = toSelectOptions(lovData?.voter_status);
    const communicationPrefOptions = toSelectOptions(lovData?.communication_pref);
    const inactiveReasonOptions = toSelectOptions(lovData?.inactive_reason);

    const updateMutation = useUpdateContactMutation();
    const deleteMutation = useDeleteContactMutation();
    const addTagMutation = useAddTagMutation();
    const removeTagMutation = useRemoveTagMutation();

    const openEditModal = (type: EditModalType) => {
        if (!contact) return;

        // Pre-fill form based on modal type
        const formValues: Record<string, unknown> = {};

        if (type === 'contact') {
            Object.assign(formValues, {
                name: contact.name,
                email: contact.email,
                phone: contact.phone,
                secondary_email: contact.secondary_email,
                mobile_phone: contact.mobile_phone,
                work_phone: contact.work_phone,
                preferred_name: contact.preferred_name,
                prefix: contact.prefix,
                first_name: contact.first_name,
                middle_name: contact.middle_name,
                last_name: contact.last_name,
                suffix: contact.suffix,
                preferred_language: contact.preferred_language,
                communication_preference: contact.communication_preference,
            });
        } else if (type === 'demographics') {
            Object.assign(formValues, {
                gender: contact.gender,
                pronouns: contact.pronouns,
                date_of_birth: contact.date_of_birth ? dayjs(contact.date_of_birth) : null,
                age_estimate: contact.age_estimate,
                marital_status: contact.marital_status,
                has_children: contact.has_children,
                household_size: contact.household_size,
                education_level: contact.education_level,
                income_bracket: contact.income_bracket,
                homeowner_status: contact.homeowner_status,
            });
        } else if (type === 'professional') {
            Object.assign(formValues, {
                occupation: contact.occupation,
                job_title: contact.job_title,
                employer: contact.employer,
                industry: contact.industry,
            });
        } else if (type === 'location') {
            Object.assign(formValues, {
                address_street: contact.address?.street,
                address_street2: contact.address?.street2,
                address_city: contact.address?.city,
                address_state: contact.address?.state,
                address_zip: contact.address?.zip,
                county: contact.county,
                congressional_district: contact.congressional_district,
                state_legislative_district: contact.state_legislative_district,
            });
        } else if (type === 'voter') {
            Object.assign(formValues, {
                voter_status: contact.voter_status,
                party_affiliation: contact.party_affiliation,
                voter_registration_date: contact.voter_registration_date
                    ? dayjs(contact.voter_registration_date)
                    : null,
            });
        } else if (type === 'status') {
            Object.assign(formValues, {
                is_active: contact.is_active,
                inactive_reason: contact.inactive_reason,
                notes: contact.notes,
            });
        }

        form.setFieldsValue(formValues);
        setEditModal(type);
    };

    const handleEditSubmit = async () => {
        try {
            const values = await form.validateFields();
            const updateData: Record<string, unknown> = {};

            if (editModal === 'contact') {
                Object.assign(updateData, {
                    name: values.name,
                    email: values.email,
                    phone: values.phone,
                    secondary_email: values.secondary_email,
                    mobile_phone: values.mobile_phone,
                    work_phone: values.work_phone,
                    preferred_name: values.preferred_name,
                    prefix: values.prefix,
                    first_name: values.first_name,
                    middle_name: values.middle_name,
                    last_name: values.last_name,
                    suffix: values.suffix,
                    preferred_language: values.preferred_language,
                    communication_preference: values.communication_preference,
                });
            } else if (editModal === 'demographics') {
                Object.assign(updateData, {
                    gender: values.gender,
                    pronouns: values.pronouns,
                    date_of_birth: values.date_of_birth?.format('YYYY-MM-DD'),
                    age_estimate: values.age_estimate,
                    marital_status: values.marital_status,
                    has_children: values.has_children,
                    household_size: values.household_size,
                    education_level: values.education_level,
                    income_bracket: values.income_bracket,
                    homeowner_status: values.homeowner_status,
                });
            } else if (editModal === 'professional') {
                Object.assign(updateData, {
                    occupation: values.occupation,
                    job_title: values.job_title,
                    employer: values.employer,
                    industry: values.industry,
                });
            } else if (editModal === 'location') {
                Object.assign(updateData, {
                    address: {
                        street: values.address_street,
                        street2: values.address_street2,
                        city: values.address_city,
                        state: values.address_state,
                        zip: values.address_zip,
                    },
                    county: values.county,
                    state: values.address_state,
                    zip_code: values.address_zip,
                    congressional_district: values.congressional_district,
                    state_legislative_district: values.state_legislative_district,
                });
            } else if (editModal === 'voter') {
                Object.assign(updateData, {
                    voter_status: values.voter_status,
                    party_affiliation: values.party_affiliation,
                    voter_registration_date: values.voter_registration_date?.format('YYYY-MM-DD'),
                });
            } else if (editModal === 'status') {
                Object.assign(updateData, {
                    is_active: values.is_active,
                    inactive_reason: values.is_active ? null : values.inactive_reason,
                    notes: values.notes,
                });
            }

            await updateMutation.mutateAsync({
                contactId: contactId!,
                data: updateData,
            });
            message.success('Contact updated successfully');
            setEditModal(null);
            form.resetFields();
            refetch();
        } catch (error) {
            if (error && typeof error === 'object' && 'errorFields' in error) {
                return;
            }
            message.error(getErrorMessage(error));
        }
    };

    const handleDelete = async () => {
        try {
            await deleteMutation.mutateAsync(contactId!);
            message.success('Contact deleted successfully');
            navigate('/contacts');
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleAddTag = async () => {
        if (!newTag.trim()) return;
        try {
            await addTagMutation.mutateAsync({
                contactId: contactId!,
                tag: newTag.trim(),
            });
            setNewTag('');
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const handleRemoveTag = async (tag: string) => {
        try {
            await removeTagMutation.mutateAsync({
                contactId: contactId!,
                tag,
            });
            refetch();
        } catch (error) {
            message.error(getErrorMessage(error));
        }
    };

    const messageColumns: ColumnsType<ContactMessageSummary> = [
        {
            title: 'Subject',
            dataIndex: 'subject',
            key: 'subject',
            ellipsis: true,
            render: (text: string, record) => <a onClick={() => navigate(`/messages/${record.id}`)}>{text}</a>,
        },
        {
            title: 'Source',
            dataIndex: 'source',
            key: 'source',
            width: 100,
            render: (source: string) => (
                <Tag color={source === 'email' ? 'blue' : source === 'form' ? 'purple' : 'cyan'}>
                    {source.toUpperCase()}
                </Tag>
            ),
        },
        {
            title: 'Tones',
            dataIndex: 'tones',
            key: 'tones',
            width: 150,
            render: (tones: ToneScore[]) => {
                if (!tones || tones.length === 0) return <Tag>Pending</Tag>;
                return (
                    <Space wrap size={[0, 4]}>
                        {tones.slice(0, 2).map((t) => (
                            <Tag key={t.label} color={getToneColor(t.label)}>
                                {t.label}
                            </Tag>
                        ))}
                    </Space>
                );
            },
        },
        {
            title: 'Status',
            dataIndex: 'processing_status',
            key: 'processing_status',
            width: 100,
            render: (status: string) => {
                const colors: Record<string, string> = {
                    pending: 'default',
                    processing: 'processing',
                    completed: 'success',
                    failed: 'error',
                };
                return <Tag color={colors[status]}>{status}</Tag>;
            },
        },
        {
            title: 'Received',
            dataIndex: 'received_at',
            key: 'received_at',
            width: 150,
            render: (date: string) => dayjs(date).format('MMM D, YYYY HH:mm'),
        },
    ];

    // Prepare chart data
    const chartData =
        timelineData?.entries.map((entry) => ({
            date: entry.date,
            sentiment: entry.avg_sentiment ?? 0,
            messages: entry.message_count,
        })) || [];

    const chartConfig = {
        data: chartData,
        xField: 'date',
        yField: 'sentiment',
        smooth: true,
        height: 200,
        xAxis: {
            label: {
                formatter: (v: string) => dayjs(v).format('MMM D'),
            },
        },
        yAxis: {
            min: -1,
            max: 1,
            label: {
                formatter: (v: number) => {
                    if (v > 0.3) return 'Positive';
                    if (v < -0.3) return 'Negative';
                    return 'Neutral';
                },
            },
        },
        tooltip: {
            formatter: (datum: { date: string; sentiment: number; messages: number }) => ({
                name: 'Sentiment',
                value: datum.sentiment.toFixed(2),
            }),
        },
        annotations: [
            {
                type: 'line',
                start: ['min', 0.3],
                end: ['max', 0.3],
                style: { stroke: '#52c41a', lineDash: [4, 4] },
            },
            {
                type: 'line',
                start: ['min', -0.3],
                end: ['max', -0.3],
                style: { stroke: '#ff4d4f', lineDash: [4, 4] },
            },
        ],
    };

    if (isLoading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
                <Spin size='large' />
            </div>
        );
    }

    if (!contact) {
        return (
            <Empty description='Contact not found'>
                <Button onClick={() => navigate('/contacts')}>Back to Contacts</Button>
            </Empty>
        );
    }

    return (
        <div>
            {/* Inactive Warning */}
            {!contact.is_active && (
                <Alert
                    message='Inactive Contact'
                    description={`This contact is marked as inactive${
                        contact.inactive_reason ? `: ${formatLabel(contact.inactive_reason)}` : ''
                    }`}
                    type='warning'
                    showIcon
                    style={{ marginBottom: 16 }}
                    action={
                        canEdit && (
                            <Button size='small' onClick={() => openEditModal('status')}>
                                Update Status
                            </Button>
                        )
                    }
                />
            )}

            {/* Header */}
            <div style={{ marginBottom: 24 }}>
                <Button
                    type='text'
                    icon={<ArrowLeftOutlined />}
                    onClick={() => navigate('/contacts')}
                    style={{ marginBottom: 8 }}
                >
                    Back to Contacts
                </Button>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <Space align='center'>
                            <Title level={2} style={{ margin: 0 }}>
                                {contact.name || contact.email}
                            </Title>
                            {!contact.is_active && <Tag color='orange'>Inactive</Tag>}
                        </Space>
                        {contact.name && (
                            <Text type='secondary' style={{ display: 'block' }}>
                                {contact.email}
                            </Text>
                        )}
                    </div>
                    {canEdit && (
                        <Popconfirm
                            title='Delete this contact?'
                            description='Messages will be preserved but unlinked.'
                            onConfirm={handleDelete}
                            okText='Delete'
                            okType='danger'
                        >
                            <Button danger icon={<DeleteOutlined />}>
                                Delete
                            </Button>
                        </Popconfirm>
                    )}
                </div>
            </div>

            <Row gutter={24}>
                {/* Left Column - Contact Info */}
                <Col xs={24} lg={8}>
                    {/* Basic Info Card */}
                    <Card
                        title={
                            <>
                                <UserOutlined /> Contact Information
                            </>
                        }
                        style={{ marginBottom: 16 }}
                        extra={
                            canEdit && (
                                <Button type='text' icon={<EditOutlined />} onClick={() => openEditModal('contact')}>
                                    Edit
                                </Button>
                            )
                        }
                    >
                        <Descriptions column={1} size='small'>
                            <Descriptions.Item label='Full Name'>
                                {contact.prefix || contact.first_name || contact.last_name
                                    ? [
                                          contact.prefix,
                                          contact.first_name,
                                          contact.middle_name,
                                          contact.last_name,
                                          contact.suffix,
                                      ]
                                          .filter(Boolean)
                                          .join(' ')
                                    : displayValue(contact.name)}
                            </Descriptions.Item>
                            {contact.preferred_name && (
                                <Descriptions.Item label='Preferred Name'>{contact.preferred_name}</Descriptions.Item>
                            )}
                            <Descriptions.Item label={<>Email</>}>
                                <Text copyable>{contact.email}</Text>
                            </Descriptions.Item>
                            {contact.secondary_email && (
                                <Descriptions.Item label='Secondary Email'>
                                    <Text copyable>{contact.secondary_email}</Text>
                                </Descriptions.Item>
                            )}
                            <Descriptions.Item label={<>Phone</>}>{displayValue(contact.phone)}</Descriptions.Item>
                            {contact.mobile_phone && (
                                <Descriptions.Item label='Mobile'>{contact.mobile_phone}</Descriptions.Item>
                            )}
                            {contact.work_phone && (
                                <Descriptions.Item label='Work Phone'>{contact.work_phone}</Descriptions.Item>
                            )}
                            <Descriptions.Item label='Preferred Contact'>
                                {formatLabel(contact.communication_preference)}
                            </Descriptions.Item>
                            <Descriptions.Item label='Language'>
                                {displayValue(contact.preferred_language) === 'N/A'
                                    ? 'N/A'
                                    : contact.preferred_language?.toUpperCase()}
                            </Descriptions.Item>
                        </Descriptions>
                    </Card>

                    {/* Demographics Card */}
                    <Card
                        title={
                            <>
                                <IdcardOutlined /> Demographics
                            </>
                        }
                        style={{ marginBottom: 16 }}
                        extra={
                            canEdit && (
                                <Button type='text' icon={<EditOutlined />} onClick={() => openEditModal('demographics')}>
                                    Edit
                                </Button>
                            )
                        }
                    >
                        <Descriptions column={1} size='small'>
                            <Descriptions.Item label='Gender'>{formatLabel(contact.gender)}</Descriptions.Item>
                            <Descriptions.Item label='Pronouns'>
                                {contact.pronouns
                                    ? pronounOptions.find((p) => p.value === contact.pronouns)?.label ||
                                      formatLabel(contact.pronouns)
                                    : 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label='Date of Birth'>
                                {contact.date_of_birth ? dayjs(contact.date_of_birth).format('MMM D, YYYY') : 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label='Age'>
                                {contact.date_of_birth
                                    ? `${dayjs().diff(dayjs(contact.date_of_birth), 'year')} years`
                                    : contact.age_estimate
                                    ? `~${contact.age_estimate} years (${contact.age_estimate_source || 'estimated'})`
                                    : 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label='Marital Status'>
                                {formatLabel(contact.marital_status)}
                            </Descriptions.Item>
                            <Descriptions.Item label='Has Children'>
                                {contact.has_children === true ? 'Yes' : contact.has_children === false ? 'No' : 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label='Household Size'>
                                {displayValue(contact.household_size)}
                            </Descriptions.Item>
                            <Descriptions.Item label='Education'>
                                {formatLabel(contact.education_level)}
                            </Descriptions.Item>
                            <Descriptions.Item label='Income Bracket'>
                                {formatLabel(contact.income_bracket)}
                            </Descriptions.Item>
                            <Descriptions.Item label='Homeowner'>
                                {formatLabel(contact.homeowner_status)}
                            </Descriptions.Item>
                        </Descriptions>
                    </Card>

                    {/* Professional Card */}
                    <Card
                        title={
                            <>
                                <BankOutlined /> Professional
                            </>
                        }
                        style={{ marginBottom: 16 }}
                        extra={
                            canEdit && (
                                <Button type='text' icon={<EditOutlined />} onClick={() => openEditModal('professional')}>
                                    Edit
                                </Button>
                            )
                        }
                    >
                        <Descriptions column={1} size='small'>
                            <Descriptions.Item label='Occupation'>{displayValue(contact.occupation)}</Descriptions.Item>
                            <Descriptions.Item label='Job Title'>{displayValue(contact.job_title)}</Descriptions.Item>
                            <Descriptions.Item label='Employer'>{displayValue(contact.employer)}</Descriptions.Item>
                            <Descriptions.Item label='Industry'>{displayValue(contact.industry)}</Descriptions.Item>
                        </Descriptions>
                    </Card>

                    {/* Address & Geographic Card */}
                    <Card
                        title={
                            <>
                                <EnvironmentOutlined /> Location & District
                            </>
                        }
                        style={{ marginBottom: 16 }}
                        extra={
                            canEdit && (
                                <Button type='text' icon={<EditOutlined />} onClick={() => openEditModal('location')}>
                                    Edit
                                </Button>
                            )
                        }
                    >
                        <Descriptions column={1} size='small'>
                            <Descriptions.Item label='Address'>
                                {contact.address
                                    ? [
                                          contact.address.street,
                                          contact.address.street2,
                                          contact.address.city,
                                          contact.address.state,
                                          contact.address.zip,
                                      ]
                                          .filter(Boolean)
                                          .join(', ')
                                    : 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label='County'>
                                {displayValue(contact.county || contact.address?.county)}
                            </Descriptions.Item>
                            <Descriptions.Item label='State'>
                                {displayValue(contact.state || contact.address?.state)}
                            </Descriptions.Item>
                            <Descriptions.Item label='ZIP Code'>
                                {displayValue(contact.zip_code || contact.address?.zip)}
                            </Descriptions.Item>
                            <Descriptions.Item label='Congressional District'>
                                {displayValue(contact.congressional_district)}
                            </Descriptions.Item>
                            <Descriptions.Item label='State Legislative District'>
                                {displayValue(contact.state_legislative_district)}
                            </Descriptions.Item>
                            {contact.latitude && contact.longitude && (
                                <Descriptions.Item label='Coordinates'>
                                    {contact.latitude.toFixed(4)}, {contact.longitude.toFixed(4)}
                                </Descriptions.Item>
                            )}
                        </Descriptions>
                    </Card>

                    {/* Voter/Political Card */}
                    <Card
                        title={
                            <>
                                <TeamOutlined /> Voter Information
                            </>
                        }
                        style={{ marginBottom: 16 }}
                        extra={
                            canEdit && (
                                <Button type='text' icon={<EditOutlined />} onClick={() => openEditModal('voter')}>
                                    Edit
                                </Button>
                            )
                        }
                    >
                        <Descriptions column={1} size='small'>
                            <Descriptions.Item label='Voter Status'>
                                <Tag
                                    color={
                                        contact.voter_status === 'active'
                                            ? 'green'
                                            : contact.voter_status === 'inactive'
                                            ? 'orange'
                                            : contact.voter_status === 'unregistered'
                                            ? 'default'
                                            : 'default'
                                    }
                                >
                                    {formatLabel(contact.voter_status)}
                                </Tag>
                            </Descriptions.Item>
                            <Descriptions.Item label='Party Affiliation'>
                                {displayValue(contact.party_affiliation)}
                            </Descriptions.Item>
                            <Descriptions.Item label='Registration Date'>
                                {contact.voter_registration_date
                                    ? dayjs(contact.voter_registration_date).format('MMM D, YYYY')
                                    : 'N/A'}
                            </Descriptions.Item>
                        </Descriptions>
                    </Card>

                    {/* Stats Card */}
                    <Card title='Activity Statistics' style={{ marginBottom: 16 }}>
                        <Row gutter={16}>
                            <Col span={12}>
                                <Statistic title='Messages' value={contact.message_count} prefix={<MailOutlined />} />
                            </Col>
                            <Col span={12}>
                                <div>
                                    <Text type='secondary' style={{ fontSize: 14 }}>
                                        Dominant Tones
                                    </Text>
                                    <div style={{ marginTop: 8 }}>
                                        {contact.dominant_tones && contact.dominant_tones.length > 0 ? (
                                            <Space wrap size={[4, 4]}>
                                                {contact.dominant_tones.slice(0, 3).map((tone) => (
                                                    <Tag key={tone} color={getToneColor(tone)}>
                                                        {tone}
                                                    </Tag>
                                                ))}
                                            </Space>
                                        ) : (
                                            <Text type='secondary'>None detected</Text>
                                        )}
                                    </div>
                                </div>
                            </Col>
                        </Row>
                        <Descriptions column={1} size='small' style={{ marginTop: 16 }}>
                            <Descriptions.Item label='Created'>
                                {contact.created_at ? dayjs(contact.created_at).format('MMM D, YYYY') : 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label='First Contact'>
                                {contact.first_contact_at
                                    ? dayjs(contact.first_contact_at).format('MMM D, YYYY')
                                    : 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label='Last Contact'>
                                {contact.last_contact_at ? dayjs(contact.last_contact_at).format('MMM D, YYYY') : 'N/A'}
                            </Descriptions.Item>
                        </Descriptions>
                    </Card>

                    {/* Tags Card */}
                    <Card
                        title={
                            <>
                                <TagOutlined /> Tags
                            </>
                        }
                        style={{ marginBottom: 16 }}
                    >
                        <Space wrap style={{ marginBottom: 12 }}>
                            {contact.tags?.map((tag) => (
                                <Tag key={tag} closable={canEdit} onClose={() => handleRemoveTag(tag)}>
                                    {tag}
                                </Tag>
                            ))}
                            {(!contact.tags || contact.tags.length === 0) && <Text type='secondary'>No tags</Text>}
                        </Space>
                        {canEdit && (
                            <Input
                                placeholder='Add tag...'
                                prefix={<PlusOutlined />}
                                value={newTag}
                                onChange={(e) => setNewTag(e.target.value)}
                                onPressEnter={handleAddTag}
                                suffix={
                                    newTag && <CloseOutlined style={{ cursor: 'pointer' }} onClick={() => setNewTag('')} />
                                }
                            />
                        )}
                    </Card>

                    {/* Custom Fields Card */}
                    {contact.custom_fields && contact.custom_fields.length > 0 && (
                        <Card title='Custom Fields' style={{ marginBottom: 16 }}>
                            <Descriptions column={1} size='small'>
                                {contact.custom_fields.map((field) => (
                                    <Descriptions.Item key={field.field_key} label={field.field_name}>
                                        {field.field_type === 'boolean'
                                            ? field.value
                                                ? 'Yes'
                                                : 'No'
                                            : Array.isArray(field.value)
                                            ? field.value.join(', ')
                                            : String(field.value ?? 'N/A')}
                                    </Descriptions.Item>
                                ))}
                            </Descriptions>
                        </Card>
                    )}

                    {/* Status & Notes Card */}
                    <Card
                        title='Status & Notes'
                        style={{ marginBottom: 16 }}
                        extra={
                            canEdit && (
                                <Button type='text' icon={<EditOutlined />} onClick={() => openEditModal('status')}>
                                    Edit
                                </Button>
                            )
                        }
                    >
                        <Descriptions column={1} size='small'>
                            <Descriptions.Item label='Status'>
                                <Tag color={contact.is_active ? 'green' : 'orange'}>
                                    {contact.is_active ? 'Active' : 'Inactive'}
                                </Tag>
                                {!contact.is_active && contact.inactive_reason && (
                                    <Text type='secondary' style={{ marginLeft: 8 }}>
                                        ({formatLabel(contact.inactive_reason)})
                                    </Text>
                                )}
                            </Descriptions.Item>
                            <Descriptions.Item label='Notes'>
                                {contact.notes || <Text type='secondary'>No notes</Text>}
                            </Descriptions.Item>
                        </Descriptions>
                    </Card>
                </Col>

                {/* Right Column - Activity */}
                <Col xs={24} lg={16}>
                    <Tabs
                        items={[
                            {
                                key: 'messages',
                                label: `Messages (${messagesData?.total || 0})`,
                                children: (
                                    <Card>
                                        <Table
                                            columns={messageColumns}
                                            dataSource={messagesData?.items}
                                            rowKey='id'
                                            loading={messagesLoading}
                                            pagination={{
                                                current: messagesPage,
                                                pageSize: messagesPageSize,
                                                total: messagesData?.total,
                                                showSizeChanger: true,
                                                showTotal: (total) => `${total} messages`,
                                                onChange: (p, ps) => {
                                                    setMessagesPage(p);
                                                    setMessagesPageSize(ps);
                                                },
                                            }}
                                            onRow={(record) => ({
                                                onClick: () => navigate(`/messages/${record.id}`),
                                                style: { cursor: 'pointer' },
                                            })}
                                        />
                                    </Card>
                                ),
                            },
                            {
                                key: 'timeline',
                                label: 'Sentiment Timeline',
                                children: (
                                    <Card>
                                        {chartData.length > 0 ? (
                                            <>
                                                <Paragraph type='secondary' style={{ marginBottom: 16 }}>
                                                    Sentiment trend over the last 90 days
                                                </Paragraph>
                                                <Line {...chartConfig} />
                                            </>
                                        ) : (
                                            <Empty description='No timeline data available' />
                                        )}
                                    </Card>
                                ),
                            },
                            {
                                key: 'voting-history',
                                label: (
                                    <span>
                                        <HistoryOutlined /> Voting History
                                    </span>
                                ),
                                children: (
                                    <Card>
                                        <Title level={5} style={{ marginBottom: 16 }}>
                                            <HistoryOutlined /> Election Participation History
                                        </Title>
                                        {contact.voter_status ? (
                                            <>
                                                <Descriptions
                                                    column={2}
                                                    size='small'
                                                    bordered
                                                    style={{ marginBottom: 24 }}
                                                >
                                                    <Descriptions.Item label='Voter Status'>
                                                        <Tag
                                                            color={
                                                                contact.voter_status === 'active'
                                                                    ? 'green'
                                                                    : contact.voter_status === 'inactive'
                                                                    ? 'orange'
                                                                    : 'default'
                                                            }
                                                        >
                                                            {formatLabel(contact.voter_status)}
                                                        </Tag>
                                                    </Descriptions.Item>
                                                    <Descriptions.Item label='Party'>
                                                        {displayValue(contact.party_affiliation)}
                                                    </Descriptions.Item>
                                                    <Descriptions.Item label='Registration Date'>
                                                        {contact.voter_registration_date
                                                            ? dayjs(contact.voter_registration_date).format(
                                                                  'MMM D, YYYY'
                                                              )
                                                            : 'N/A'}
                                                    </Descriptions.Item>
                                                    <Descriptions.Item label='District'>
                                                        {displayValue(contact.congressional_district)}
                                                    </Descriptions.Item>
                                                </Descriptions>

                                                {voteSummaryData && voteSummaryData.total_elections > 0 && (
                                                    <Card type='inner' title='Voting Summary' style={{ marginBottom: 16 }}>
                                                        <Row gutter={16}>
                                                            <Col span={6}>
                                                                <Statistic
                                                                    title='Vote Rate'
                                                                    value={voteSummaryData.vote_rate}
                                                                    suffix='%'
                                                                    precision={1}
                                                                    valueStyle={{
                                                                        color: voteSummaryData.vote_rate >= 70 ? '#52c41a' : voteSummaryData.vote_rate >= 40 ? '#faad14' : '#ff4d4f',
                                                                    }}
                                                                />
                                                            </Col>
                                                            <Col span={6}>
                                                                <Statistic
                                                                    title='Elections Voted'
                                                                    value={voteSummaryData.elections_voted}
                                                                    suffix={`/ ${voteSummaryData.total_elections}`}
                                                                />
                                                            </Col>
                                                            <Col span={6}>
                                                                <Statistic
                                                                    title='General Elections'
                                                                    value={voteSummaryData.general_elections_voted}
                                                                />
                                                            </Col>
                                                            <Col span={6}>
                                                                <Statistic
                                                                    title='Primary Elections'
                                                                    value={voteSummaryData.primary_elections_voted}
                                                                />
                                                            </Col>
                                                        </Row>
                                                        {voteSummaryData.last_voted_date && (
                                                            <Paragraph type='secondary' style={{ marginTop: 16, marginBottom: 0 }}>
                                                                Last voted: {dayjs(voteSummaryData.last_voted_date).format('MMM D, YYYY')} ({voteSummaryData.last_voted_election})
                                                                {voteSummaryData.most_common_method && (
                                                                    <> | Preferred method: {formatVotingMethod(voteSummaryData.most_common_method)}</>
                                                                )}
                                                            </Paragraph>
                                                        )}
                                                    </Card>
                                                )}

                                                <Title level={5} style={{ marginBottom: 16 }}>
                                                    Election History
                                                </Title>
                                                <Table
                                                    dataSource={voteHistoryData?.items || []}
                                                    loading={voteHistoryLoading}
                                                    columns={[
                                                        {
                                                            title: 'Election',
                                                            dataIndex: 'election_name',
                                                            key: 'election_name',
                                                        },
                                                        {
                                                            title: 'Date',
                                                            dataIndex: 'election_date',
                                                            key: 'election_date',
                                                            render: (date: string) =>
                                                                date ? dayjs(date).format('MMM D, YYYY') : 'N/A',
                                                        },
                                                        {
                                                            title: 'Type',
                                                            dataIndex: 'election_type',
                                                            key: 'election_type',
                                                            render: (type: string) => (
                                                                <Tag
                                                                    color={
                                                                        type === 'general'
                                                                            ? 'blue'
                                                                            : type === 'primary'
                                                                            ? 'purple'
                                                                            : 'default'
                                                                    }
                                                                >
                                                                    {formatElectionType(type)}
                                                                </Tag>
                                                            ),
                                                        },
                                                        {
                                                            title: 'Voted',
                                                            dataIndex: 'voted',
                                                            key: 'voted',
                                                            render: (voted: boolean | null) => {
                                                                if (voted === true)
                                                                    return (
                                                                        <CheckCircleOutlined
                                                                            style={{ color: '#52c41a', fontSize: 18 }}
                                                                        />
                                                                    );
                                                                if (voted === false)
                                                                    return (
                                                                        <CloseCircleOutlined
                                                                            style={{ color: '#ff4d4f', fontSize: 18 }}
                                                                        />
                                                                    );
                                                                return (
                                                                    <QuestionCircleOutlined
                                                                        style={{ color: '#d9d9d9', fontSize: 18 }}
                                                                    />
                                                                );
                                                            },
                                                        },
                                                        {
                                                            title: 'Method',
                                                            dataIndex: 'voting_method',
                                                            key: 'voting_method',
                                                            render: (method: string) =>
                                                                method ? formatVotingMethod(method) : 'N/A',
                                                        },
                                                    ]}
                                                    rowKey='id'
                                                    pagination={{
                                                        total: voteHistoryData?.total || 0,
                                                        pageSize: voteHistoryData?.page_size || 20,
                                                        current: voteHistoryData?.page || 1,
                                                        showSizeChanger: false,
                                                        showTotal: (total) => `${total} elections`,
                                                    }}
                                                    locale={{
                                                        emptyText: (
                                                            <Empty
                                                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                                                                description={
                                                                    <span>
                                                                        No voting history records
                                                                        <br />
                                                                        <Text type='secondary'>
                                                                            Import voter files to populate election
                                                                            participation history
                                                                        </Text>
                                                                    </span>
                                                                }
                                                            />
                                                        ),
                                                    }}
                                                />
                                            </>
                                        ) : (
                                            <Empty
                                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                                                description={
                                                    <span>
                                                        Voter information not available
                                                        <br />
                                                        <Text type='secondary'>
                                                            Add voter registration details in the Voter Information
                                                            section
                                                        </Text>
                                                    </span>
                                                }
                                            >
                                                {canEdit && (
                                                    <Button type='primary' onClick={() => openEditModal('voter')}>
                                                        Add Voter Info
                                                    </Button>
                                                )}
                                            </Empty>
                                        )}
                                    </Card>
                                ),
                            },
                            {
                                key: 'analysis',
                                label: (
                                    <span>
                                        <BulbOutlined /> Analysis
                                    </span>
                                ),
                                children: (
                                    <Card>
                                        <Title level={5} style={{ marginBottom: 16 }}>
                                            <RobotOutlined /> AI-Powered Contact Analysis
                                        </Title>

                                        {/* Engagement Score Section */}
                                        <Card type='inner' title='Engagement Score' style={{ marginBottom: 16 }}>
                                            <Row gutter={24} align='middle'>
                                                <Col span={8}>
                                                    <Statistic
                                                        title='Overall Score'
                                                        value={
                                                            contact.message_count > 0
                                                                ? Math.min(100, contact.message_count * 10 + 20)
                                                                : 0
                                                        }
                                                        suffix='/ 100'
                                                        valueStyle={{
                                                            color:
                                                                contact.message_count > 5
                                                                    ? '#52c41a'
                                                                    : contact.message_count > 0
                                                                    ? '#faad14'
                                                                    : '#d9d9d9',
                                                        }}
                                                    />
                                                </Col>
                                                <Col span={16}>
                                                    <Text type='secondary'>
                                                        Based on message frequency, tone patterns, and interaction
                                                        history.
                                                        {contact.message_count === 0 && ' No messages recorded yet.'}
                                                    </Text>
                                                </Col>
                                            </Row>
                                        </Card>

                                        {/* Recommendations Section */}
                                        <Card
                                            type='inner'
                                            title={
                                                <Space>
                                                    <BulbOutlined />
                                                    <span>Recommendations</span>
                                                    <Tag color='blue'>Coming Soon</Tag>
                                                </Space>
                                            }
                                            style={{ marginBottom: 16 }}
                                        >
                                            <Alert
                                                message='AI Recommendations'
                                                description={
                                                    <div>
                                                        <Paragraph style={{ marginBottom: 8 }}>
                                                            This section will provide AI-generated recommendations to
                                                            encourage participation from this contact, including:
                                                        </Paragraph>
                                                        <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                                                            <li>
                                                                Personalized outreach suggestions based on communication
                                                                tone
                                                            </li>
                                                            <li>
                                                                Optimal contact timing based on historical engagement
                                                            </li>
                                                            <li>
                                                                Issue-based talking points aligned with expressed
                                                                interests
                                                            </li>
                                                            <li>
                                                                Event invitations relevant to their location and
                                                                demographics
                                                            </li>
                                                            <li>Volunteer opportunities matching their profile</li>
                                                        </ul>
                                                    </div>
                                                }
                                                type='info'
                                                showIcon
                                                icon={<RobotOutlined />}
                                            />
                                        </Card>

                                        {/* Contact Insights */}
                                        <Card type='inner' title='Contact Insights' style={{ marginBottom: 16 }}>
                                            <Descriptions column={1} size='small'>
                                                <Descriptions.Item label='Communication Pattern'>
                                                    {contact.message_count > 10
                                                        ? 'Highly engaged - Regular communicator'
                                                        : contact.message_count > 5
                                                        ? 'Moderately engaged - Periodic communicator'
                                                        : contact.message_count > 0
                                                        ? 'Low engagement - Occasional communicator'
                                                        : 'No communications recorded'}
                                                </Descriptions.Item>
                                                <Descriptions.Item label='Dominant Communication Tones'>
                                                    {contact.dominant_tones && contact.dominant_tones.length > 0 ? (
                                                        <Space wrap>
                                                            {contact.dominant_tones.map((tone) => (
                                                                <Tag key={tone} color={getToneColor(tone)}>
                                                                    {tone}
                                                                </Tag>
                                                            ))}
                                                        </Space>
                                                    ) : (
                                                        <Text type='secondary'>Not enough data</Text>
                                                    )}
                                                </Descriptions.Item>
                                                <Descriptions.Item label='Contact Completeness'>
                                                    {(() => {
                                                        const fields = [
                                                            contact.name,
                                                            contact.phone,
                                                            contact.address,
                                                            contact.voter_status,
                                                            contact.party_affiliation,
                                                            contact.occupation,
                                                            contact.date_of_birth,
                                                        ];
                                                        const filled = fields.filter(Boolean).length;
                                                        const percentage = Math.round((filled / fields.length) * 100);
                                                        return (
                                                            <Space>
                                                                <Tag
                                                                    color={
                                                                        percentage > 70
                                                                            ? 'green'
                                                                            : percentage > 40
                                                                            ? 'orange'
                                                                            : 'red'
                                                                    }
                                                                >
                                                                    {percentage}% complete
                                                                </Tag>
                                                                <Text type='secondary'>
                                                                    ({filled} of {fields.length} key fields)
                                                                </Text>
                                                            </Space>
                                                        );
                                                    })()}
                                                </Descriptions.Item>
                                                <Descriptions.Item label='Last Activity'>
                                                    {contact.last_contact_at
                                                        ? `${dayjs(contact.last_contact_at).format(
                                                              'MMM D, YYYY'
                                                          )} (${dayjs(contact.last_contact_at).fromNow()})`
                                                        : 'No activity recorded'}
                                                </Descriptions.Item>
                                            </Descriptions>
                                        </Card>

                                        {/* Action Items */}
                                        <Card type='inner' title='Suggested Actions'>
                                            <Space direction='vertical' style={{ width: '100%' }}>
                                                {!contact.phone && (
                                                    <Alert
                                                        message='Add phone number'
                                                        description='Phone contact information can improve outreach success.'
                                                        type='warning'
                                                        showIcon
                                                        action={
                                                            canEdit && (
                                                                <Button
                                                                    size='small'
                                                                    onClick={() => openEditModal('contact')}
                                                                >
                                                                    Add
                                                                </Button>
                                                            )
                                                        }
                                                    />
                                                )}
                                                {!contact.voter_status && (
                                                    <Alert
                                                        message='Add voter registration info'
                                                        description='Voter information helps with targeted civic engagement.'
                                                        type='warning'
                                                        showIcon
                                                        action={
                                                            canEdit && (
                                                                <Button size='small' onClick={() => openEditModal('voter')}>
                                                                    Add
                                                                </Button>
                                                            )
                                                        }
                                                    />
                                                )}
                                                {!contact.address && (
                                                    <Alert
                                                        message='Add address'
                                                        description='Location data enables geographic targeting and event invitations.'
                                                        type='warning'
                                                        showIcon
                                                        action={
                                                            canEdit && (
                                                                <Button
                                                                    size='small'
                                                                    onClick={() => openEditModal('location')}
                                                                >
                                                                    Add
                                                                </Button>
                                                            )
                                                        }
                                                    />
                                                )}
                                                {contact.phone && contact.voter_status && contact.address && (
                                                    <Alert
                                                        message='Profile looks complete!'
                                                        description='This contact has comprehensive information for engagement.'
                                                        type='success'
                                                        showIcon
                                                    />
                                                )}
                                            </Space>
                                        </Card>
                                    </Card>
                                ),
                            },
                        ]}
                    />
                </Col>
            </Row>

            {/* Edit Contact Info Modal */}
            <Modal
                title='Edit Contact Information'
                open={editModal === 'contact'}
                onOk={handleEditSubmit}
                onCancel={() => {
                    setEditModal(null);
                    form.resetFields();
                }}
                confirmLoading={updateMutation.isPending}
                width={600}
            >
                <Form form={form} layout='vertical'>
                    <Row gutter={16}>
                        <Col span={8}>
                            <Form.Item name='prefix' label='Prefix'>
                                <Select options={prefixOptions} allowClear placeholder='Select prefix' />
                            </Form.Item>
                        </Col>
                        <Col span={8}>
                            <Form.Item name='first_name' label='First Name'>
                                <Input />
                            </Form.Item>
                        </Col>
                        <Col span={8}>
                            <Form.Item name='middle_name' label='Middle'>
                                <Input />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name='last_name' label='Last Name'>
                                <Input />
                            </Form.Item>
                        </Col>
                        <Col span={6}>
                            <Form.Item name='suffix' label='Suffix'>
                                <Input placeholder='Jr., Sr.' />
                            </Form.Item>
                        </Col>
                        <Col span={6}>
                            <Form.Item name='preferred_name' label='Preferred Name'>
                                <Input />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item name='name' label='Display Name (fallback)'>
                        <Input placeholder='Full display name if not using name components' />
                    </Form.Item>
                    <Form.Item
                        name='email'
                        label='Email'
                        rules={[
                            { required: true, message: 'Email is required' },
                            { type: 'email', message: 'Please enter a valid email' },
                        ]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item name='secondary_email' label='Secondary Email'>
                        <Input />
                    </Form.Item>
                    <Row gutter={16}>
                        <Col span={8}>
                            <Form.Item name='phone' label='Phone'>
                                <Input />
                            </Form.Item>
                        </Col>
                        <Col span={8}>
                            <Form.Item name='mobile_phone' label='Mobile'>
                                <Input />
                            </Form.Item>
                        </Col>
                        <Col span={8}>
                            <Form.Item name='work_phone' label='Work'>
                                <Input />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name='preferred_language' label='Preferred Language'>
                                <Select options={languageOptions} allowClear placeholder='Select language' />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name='communication_preference' label='Contact Preference'>
                                <Select options={communicationPrefOptions} allowClear placeholder='Select preference' />
                            </Form.Item>
                        </Col>
                    </Row>
                </Form>
            </Modal>

            {/* Edit Demographics Modal */}
            <Modal
                title='Edit Demographics'
                open={editModal === 'demographics'}
                onOk={handleEditSubmit}
                onCancel={() => {
                    setEditModal(null);
                    form.resetFields();
                }}
                confirmLoading={updateMutation.isPending}
                width={600}
            >
                <Form form={form} layout='vertical'>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name='gender' label='Gender'>
                                <Select options={genderOptions} allowClear placeholder='Select gender' />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name='pronouns' label='Pronouns'>
                                <Select options={pronounOptions} allowClear placeholder='Select pronouns' />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name='date_of_birth' label='Date of Birth'>
                                <DatePicker style={{ width: '100%' }} />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name='age_estimate' label='Age Estimate (if DOB unknown)'>
                                <InputNumber min={0} max={120} style={{ width: '100%' }} />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name='marital_status' label='Marital Status'>
                                <Select options={maritalStatusOptions} allowClear placeholder='Select status' />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name='household_size' label='Household Size'>
                                <InputNumber min={1} max={20} style={{ width: '100%' }} />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name='has_children' label='Has Children' valuePropName='checked'>
                                <Switch checkedChildren='Yes' unCheckedChildren='No' />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name='education_level' label='Education Level'>
                                <Select options={educationOptions} allowClear placeholder='Select level' />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name='income_bracket' label='Income Bracket'>
                                <Select options={incomeOptions} allowClear placeholder='Select range' />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item name='homeowner_status' label='Homeowner Status'>
                        <Select options={homeownerOptions} allowClear placeholder='Select status' />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Edit Professional Modal */}
            <Modal
                title='Edit Professional Information'
                open={editModal === 'professional'}
                onOk={handleEditSubmit}
                onCancel={() => {
                    setEditModal(null);
                    form.resetFields();
                }}
                confirmLoading={updateMutation.isPending}
            >
                <Form form={form} layout='vertical'>
                    <Form.Item name='occupation' label='Occupation'>
                        <Input />
                    </Form.Item>
                    <Form.Item name='job_title' label='Job Title'>
                        <Input />
                    </Form.Item>
                    <Form.Item name='employer' label='Employer'>
                        <Input />
                    </Form.Item>
                    <Form.Item name='industry' label='Industry'>
                        <Input />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Edit Location Modal */}
            <Modal
                title='Edit Location & District'
                open={editModal === 'location'}
                onOk={handleEditSubmit}
                onCancel={() => {
                    setEditModal(null);
                    form.resetFields();
                }}
                confirmLoading={updateMutation.isPending}
                width={600}
            >
                <Form form={form} layout='vertical'>
                    <Form.Item name='address_street' label='Street Address'>
                        <Input />
                    </Form.Item>
                    <Form.Item name='address_street2' label='Street Address 2'>
                        <Input placeholder='Apt, Suite, Unit, etc.' />
                    </Form.Item>
                    <Row gutter={16}>
                        <Col span={10}>
                            <Form.Item name='address_city' label='City'>
                                <Input />
                            </Form.Item>
                        </Col>
                        <Col span={6}>
                            <Form.Item name='address_state' label='State'>
                                <Input placeholder='CA, NY, etc.' maxLength={2} />
                            </Form.Item>
                        </Col>
                        <Col span={8}>
                            <Form.Item name='address_zip' label='ZIP Code'>
                                <Input />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item name='county' label='County'>
                        <Input />
                    </Form.Item>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name='congressional_district' label='Congressional District'>
                                <Input placeholder='e.g., CA-12' />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name='state_legislative_district' label='State Legislative District'>
                                <Input />
                            </Form.Item>
                        </Col>
                    </Row>
                </Form>
            </Modal>

            {/* Edit Voter Modal */}
            <Modal
                title='Edit Voter Information'
                open={editModal === 'voter'}
                onOk={handleEditSubmit}
                onCancel={() => {
                    setEditModal(null);
                    form.resetFields();
                }}
                confirmLoading={updateMutation.isPending}
            >
                <Form form={form} layout='vertical'>
                    <Form.Item name='voter_status' label='Voter Status'>
                        <Select options={voterStatusOptions} allowClear placeholder='Select status' />
                    </Form.Item>
                    <Form.Item name='party_affiliation' label='Party Affiliation'>
                        <Input placeholder='Democrat, Republican, Independent, etc.' />
                    </Form.Item>
                    <Form.Item name='voter_registration_date' label='Registration Date'>
                        <DatePicker style={{ width: '100%' }} />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Edit Status & Notes Modal */}
            <Modal
                title='Edit Status & Notes'
                open={editModal === 'status'}
                onOk={handleEditSubmit}
                onCancel={() => {
                    setEditModal(null);
                    form.resetFields();
                }}
                confirmLoading={updateMutation.isPending}
            >
                <Form form={form} layout='vertical'>
                    <Form.Item name='is_active' label='Active Status' valuePropName='checked'>
                        <Switch checkedChildren='Active' unCheckedChildren='Inactive' />
                    </Form.Item>
                    <Form.Item
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => prevValues.is_active !== currentValues.is_active}
                    >
                        {({ getFieldValue }) =>
                            !getFieldValue('is_active') && (
                                <Form.Item name='inactive_reason' label='Reason for Inactivity'>
                                    <Select options={inactiveReasonOptions} allowClear placeholder='Select reason' />
                                </Form.Item>
                            )
                        }
                    </Form.Item>
                    <Form.Item name='notes' label='Notes'>
                        <Input.TextArea rows={4} placeholder='Internal notes about this contact...' />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
