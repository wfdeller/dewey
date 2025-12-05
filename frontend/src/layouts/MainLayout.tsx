import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, Space, Button, Badge, theme } from 'antd';
import {
    DashboardOutlined,
    MailOutlined,
    TeamOutlined,
    TagsOutlined,
    FlagOutlined,
    ThunderboltOutlined,
    FormOutlined,
    FileTextOutlined,
    BarChartOutlined,
    SettingOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    UserOutlined,
    LogoutOutlined,
    BulbOutlined,
    UploadOutlined,
    SyncOutlined,
    CheckCircleOutlined,
} from '@ant-design/icons';
import { useUIStore, useAuthStore } from '../stores';
import { useActiveJobsQuery } from '../services/voterImportService';

const { Header, Sider, Content } = Layout;

const menuItems = [
    {
        key: '/dashboard',
        icon: <DashboardOutlined />,
        label: 'Dashboard',
    },
    {
        key: '/messages',
        icon: <MailOutlined />,
        label: 'Messages',
    },
    {
        key: '/contacts',
        icon: <TeamOutlined />,
        label: 'Contacts',
    },
    {
        key: '/voter-import',
        icon: <UploadOutlined />,
        label: 'Voter Import',
    },
    {
        key: '/categories',
        icon: <TagsOutlined />,
        label: 'Categories',
    },
    {
        key: '/campaigns',
        icon: <FlagOutlined />,
        label: 'Campaigns',
    },
    {
        key: '/workflows',
        icon: <ThunderboltOutlined />,
        label: 'Workflows',
    },
    {
        key: '/forms',
        icon: <FormOutlined />,
        label: 'Forms',
    },
    {
        key: '/email-templates',
        icon: <FileTextOutlined />,
        label: 'Email Templates',
    },
    {
        key: '/analytics',
        icon: <BarChartOutlined />,
        label: 'Analytics',
    },
    {
        key: '/settings',
        icon: <SettingOutlined />,
        label: 'Settings',
    },
];

export default function MainLayout() {
    const navigate = useNavigate();
    const location = useLocation();
    const { token } = theme.useToken();

    const { sidebarCollapsed, toggleSidebar, darkMode, toggleDarkMode } = useUIStore();
    const { user, logout } = useAuthStore();
    const { data: activeJobsData } = useActiveJobsQuery();

    const [selectedKeys, setSelectedKeys] = useState([location.pathname]);

    const handleMenuClick = ({ key }: { key: string }) => {
        setSelectedKeys([key]);
        navigate(key);
    };

    const userMenuItems = [
        {
            key: 'profile',
            icon: <UserOutlined />,
            label: 'Profile',
            onClick: () => navigate('/profile'),
        },
        {
            key: 'settings',
            icon: <SettingOutlined />,
            label: 'Settings',
            onClick: () => navigate('/settings'),
        },
        {
            type: 'divider' as const,
        },
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: 'Logout',
            onClick: () => {
                logout();
                navigate('/login');
            },
        },
    ];

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider trigger={null} collapsible collapsed={sidebarCollapsed} theme='dark' width={220}>
                <div
                    style={{
                        height: 64,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderBottom: '1px solid rgba(255,255,255,0.1)',
                    }}
                >
                    <h1
                        style={{
                            color: 'white',
                            margin: 0,
                            fontSize: sidebarCollapsed ? 20 : 24,
                            fontWeight: 600,
                        }}
                    >
                        {sidebarCollapsed ? 'D' : 'Dewey'}
                    </h1>
                </div>
                <Menu
                    theme='dark'
                    mode='inline'
                    selectedKeys={selectedKeys}
                    items={menuItems}
                    onClick={handleMenuClick}
                    style={{ borderRight: 0 }}
                />
            </Sider>

            <Layout>
                <Header
                    style={{
                        padding: '0 24px',
                        background: token.colorBgContainer,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        borderBottom: `1px solid ${token.colorBorderSecondary}`,
                    }}
                >
                    <Button
                        type='text'
                        icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                        onClick={toggleSidebar}
                        style={{ fontSize: 16, width: 40, height: 40 }}
                    />

                    <Space size='middle'>
                        <Badge
                            count={activeJobsData?.activeCount || 0}
                            size='small'
                            offset={[-2, 2]}
                        >
                            <Button
                                type='text'
                                icon={activeJobsData?.hasActive ? <SyncOutlined spin /> : <CheckCircleOutlined />}
                                onClick={() => navigate('/jobs')}
                                title={activeJobsData?.hasActive ? `${activeJobsData.activeCount} active job(s)` : 'View job history'}
                                style={{
                                    color: activeJobsData?.hasActive ? token.colorPrimary : token.colorTextSecondary,
                                }}
                            >
                                {!sidebarCollapsed && 'Jobs'}
                            </Button>
                        </Badge>

                        <Button
                            type='text'
                            icon={<BulbOutlined />}
                            onClick={toggleDarkMode}
                            title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
                        />

                        <Dropdown menu={{ items: userMenuItems }} placement='bottomRight' arrow>
                            <Space style={{ cursor: 'pointer' }}>
                                <Avatar icon={<UserOutlined />} />
                                {!sidebarCollapsed && <span>{user?.name || 'User'}</span>}
                            </Space>
                        </Dropdown>
                    </Space>
                </Header>

                <Content
                    style={{
                        margin: 24,
                        padding: 24,
                        background: token.colorBgContainer,
                        borderRadius: token.borderRadiusLG,
                        minHeight: 280,
                        overflow: 'auto',
                    }}
                >
                    <Outlet />
                </Content>
            </Layout>
        </Layout>
    );
}
