import React, { useState } from 'react';
import {
  Layout,
  Menu,
  Avatar,
  Dropdown,
  Typography,
  Space,
  theme
} from 'antd';
import {
  HomeOutlined,
  CustomerServiceOutlined,
  UserOutlined,
  LogoutOutlined,
  DownOutlined,
  TeamOutlined,
  DollarOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks';
import { ROUTES } from '../../constants';
import styles from './MainLayout.module.css';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  // 监听屏幕尺寸变化
  React.useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    handleResize(); // 初始化
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 菜单项配置
  const menuItems = [
    {
      key: ROUTES.HOME,
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: ROUTES.CUSTOMER_SERVICE,
      icon: <CustomerServiceOutlined />,
      label: '专属客服列表',
    },
    {
      key: ROUTES.STUDENT_MODULE,
      icon: <TeamOutlined />,
      label: '学生模块',
    },
    {
      key: ROUTES.STUDENT_INCOME,
      icon: <DollarOutlined />,
      label: '收入统计',
    },
    {
      key: ROUTES.TEST_INCOME,
      icon: <DollarOutlined />,
      label: 'API测试',
    },
  ];

  // 用户下拉菜单配置
  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
      onClick: () => {
        // TODO: 跳转到个人资料页面
        console.log('跳转到个人资料');
      }
    },
    {
      type: 'divider'
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: logout
    }
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <Layout className={styles.layout}>
      {/* 侧边栏 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        className={styles.sider}
        width={200}
        collapsedWidth={80}
        breakpoint="lg"
        onBreakpoint={(broken) => {
          setCollapsed(broken);
        }}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        {/* Logo区域 */}
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <CustomerServiceOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
          </div>
          {!collapsed && (
            <div className={styles.logoText}>
              <Text strong style={{ color: '#fff', fontSize: '16px' }}>
                虚拟订单系统
              </Text>
            </div>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          className={styles.menu}
        />
      </Sider>

      {/* 主要内容区域 */}
      <Layout className={`${styles.rightLayout} ${collapsed ? styles.collapsed : ''}`}>
        {/* 顶部导航栏 */}
        <Header 
          style={{ 
            padding: '0 24px', 
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
          className={styles.header}
        >
          {/* 左侧：折叠按钮和面包屑 */}
          <Space size="large">
            <div
              className={styles.trigger}
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? '☰' : '✕'}
            </div>
            <Text style={{ fontSize: '16px', color: '#666' }}>
              Hi ~ 欢迎回来！
            </Text>
          </Space>

          {/* 右侧：用户信息 */}
          <Space size="large" align="center">
            <Dropdown
              menu={{ items: userMenuItems }}
              placement="bottomRight"
              arrow
            >
              <Space className={styles['user-dropdown']}>
                <Avatar
                  size="default"
                  icon={<UserOutlined />}
                  style={{ backgroundColor: '#1890ff' }}
                />
                <Text style={{ fontSize: '14px', fontWeight: 500 }}>
                  {user?.username || '管理员'}
                </Text>
                <DownOutlined style={{ fontSize: '12px', color: '#999' }} />
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* 内容区域 */}
        <Content
          style={{
            margin: isMobile ? '12px 8px' : '16px 24px',
            padding: isMobile ? '16px 12px' : '20px 24px',
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
          }}
          className={styles.content}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
