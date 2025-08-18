import React, { useState, useEffect } from 'react';
import {
  Typography,
  Space,
  Card,
  Row,
  Col,
  message,
  Spin,
  Button
} from 'antd';
import { useAuth } from '../../../hooks';
import {
  Loading,
  VirtualOrderStatsChart,
  StudentPoolTable
} from '../../../components';
import {
  getVirtualOrderStats,
  getStudentPools,
  getVirtualTaskGenerationConfig,
  updateVirtualTaskGenerationConfig,
  type VirtualOrderStats,
  type StudentPoolItem,
  type VirtualTaskGenerationConfig
} from '../../../api';
import styles from './index.module.css';

const { Text } = Typography;

const Home: React.FC = () => {
  const { user, loading, logout } = useAuth();

  // 数据状态
  const [statsData, setStatsData] = useState<VirtualOrderStats | null>(null);
  const [studentPools, setStudentPools] = useState<StudentPoolItem[]>([]);
  const [statsLoading, setStatsLoading] = useState(false);
  const [poolsLoading, setPoolsLoading] = useState(false);
  const [poolsPagination, setPoolsPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // 虚拟任务生成配置状态
  const [taskGenerationConfig, setTaskGenerationConfig] = useState<VirtualTaskGenerationConfig | null>(null);
  const [taskGenerationLoading, setTaskGenerationLoading] = useState(false);

  // 获取虚拟订单统计数据
  const fetchStatsData = async () => {
    try {
      setStatsLoading(true);
      const data = await getVirtualOrderStats();

      // 验证数据结构
      if (data && typeof data === 'object') {
        setStatsData(data);
      } else {
        console.error('统计数据格式异常:', data);
        message.error('统计数据格式异常');
        setStatsData(null);
      }
    } catch (error) {
      message.error('获取统计数据失败');
      console.error('获取统计数据失败:', error);
      setStatsData(null);
    } finally {
      setStatsLoading(false);
    }
  };

  // 获取学生补贴池数据
  const fetchStudentPools = async (page = 1, size = 10) => {
    try {
      setPoolsLoading(true);
      const data = await getStudentPools({ page, size });

      // 验证返回的数据结构
      if (data && typeof data === 'object' && Array.isArray(data.items)) {
        setStudentPools(data.items);
        setPoolsPagination({
          current: data.page || page,
          pageSize: data.size || size,
          total: data.total || 0
        });
      } else {
        console.error('学生补贴池数据格式异常:', data);
        message.error('学生补贴池数据格式异常');
        // 设置空数据以避免界面错误
        setStudentPools([]);
        setPoolsPagination({
          current: page,
          pageSize: size,
          total: 0
        });
      }
    } catch (error) {
      message.error('获取学生补贴池数据失败');
      console.error('获取学生补贴池数据失败:', error);
      // 设置空数据以避免界面错误
      setStudentPools([]);
      setPoolsPagination({
        current: page,
        pageSize: size,
        total: 0
      });
    } finally {
      setPoolsLoading(false);
    }
  };

  // 获取虚拟任务生成配置
  const fetchTaskGenerationConfig = async () => {
    try {
      setTaskGenerationLoading(true);
      const config = await getVirtualTaskGenerationConfig();

      // 验证配置数据
      if (config && typeof config === 'object') {
        setTaskGenerationConfig(config);
      } else {
        console.error('虚拟任务生成配置数据格式异常:', config);
        message.error('虚拟任务生成配置数据格式异常');
        setTaskGenerationConfig(null);
      }
    } catch (error) {
      message.error('获取虚拟任务生成配置失败');
      console.error('获取虚拟任务生成配置失败:', error);
      setTaskGenerationConfig(null);
    } finally {
      setTaskGenerationLoading(false);
    }
  };

  // 切换虚拟任务生成状态
  const toggleTaskGeneration = async () => {
    if (!taskGenerationConfig) return;

    try {
      setTaskGenerationLoading(true);
      const newEnabled = !taskGenerationConfig.enabled;

      const updatedConfig = await updateVirtualTaskGenerationConfig({
        enabled: newEnabled
      });

      // 验证更新后的配置数据
      if (updatedConfig && typeof updatedConfig === 'object') {
        setTaskGenerationConfig(updatedConfig);
        message.success(`虚拟任务生成已${newEnabled ? '启用' : '暂停'}`);
      } else {
        console.error('更新后的配置数据格式异常:', updatedConfig);
        message.error('更新配置成功，但返回数据格式异常');
        // 重新获取配置以确保数据一致性
        fetchTaskGenerationConfig();
      }
    } catch (error) {
      message.error('更新虚拟任务生成配置失败');
      console.error('更新虚拟任务生成配置失败:', error);
    } finally {
      setTaskGenerationLoading(false);
    }
  };

  // 处理分页变化
  const handlePageChange = (page: number, size?: number) => {
    fetchStudentPools(page, size || poolsPagination.pageSize);
  };

  // 组件挂载时获取数据
  useEffect(() => {
    if (user) {
      fetchStatsData();
      fetchStudentPools();
      fetchTaskGenerationConfig();
    }
  }, [user]);

  // 加载状态处理
  if (loading) {
    return <Loading tip="加载用户信息..." />;
  }

  // 用户未登录处理
  if (!user) {
    return null;
  }

  return (
    <div className={styles.container}>
      {/* 欢迎卡片 */}
      <Card className={styles.welcomeCard}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} lg={12}>
            <Space direction="vertical" size="small">
              <Text className={styles.title}>
                虚拟订单管理系统
              </Text>
              <Text type="secondary" className={styles.subtitle}>
                当前登录用户：{user.username}
              </Text>
              <Text type="secondary" className={styles.time}>
                登录时间：{new Date().toLocaleString()}
              </Text>
            </Space>
          </Col>
          <Col xs={24} lg={6}>
            <div className={styles.taskGenerationControl}>
              <Button
                className={`${styles.taskGenerationButton} ${
                  taskGenerationConfig?.enabled ? styles.enabled : styles.disabled
                }`}
                loading={taskGenerationLoading}
                onClick={toggleTaskGeneration}
                disabled={!taskGenerationConfig}
              >
                {taskGenerationConfig?.enabled ? '暂停生成' : '启用生成'}
              </Button>
              <Text className={styles.taskGenerationStatus}>
                虚拟任务生成：{taskGenerationConfig?.enabled ? '运行中' : '已暂停'}
              </Text>
            </div>
          </Col>
          <Col xs={24} lg={6} style={{ textAlign: 'center' }}>
            <div className={styles.avatar}>
              <img
                src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMzIiIGN5PSIzMiIgcj0iMzIiIGZpbGw9IiMxODkwZmYiLz4KPHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeD0iMTYiIHk9IjE2Ij4KPHBhdGggZD0iTTEyIDEyQzE0LjIwOTEgMTIgMTYgMTAuMjA5MSAxNiA4QzE2IDUuNzkwODYgMTQuMjA5MSA0IDEyIDRDOS43OTA4NiA0IDggNS43OTA4NiA4IDhDOCAxMC4yMDkxIDkuNzkwODYgMTIgMTIgMTJaIiBmaWxsPSJ3aGl0ZSIvPgo8cGF0aCBkPSJNMTIgMTRDOC4xMzQwMSAxNCA1IDE3LjEzNDAxIDUgMjFIMTlDMTkgMTcuMTM0MDEgMTUuODY2IDE0IDEyIDE0WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo="
                alt="用户头像"
                className={styles.avatarImg}
              />
            </div>
          </Col>
        </Row>
      </Card>

      {/* 虚拟订单统计图表 */}
      <div className={styles.chartSection}>
        {statsData ? (
          <VirtualOrderStatsChart
            data={statsData}
            loading={statsLoading}
          />
        ) : (
          <Card>
            <div className={styles.loading}>
              <Spin size="large" />
              <div className={styles.loadingText}>加载统计数据中...</div>
            </div>
          </Card>
        )}
      </div>

      {/* 学生补贴池列表 */}
      <div className={styles.tableSection}>
        <StudentPoolTable
          data={studentPools}
          loading={poolsLoading}
          total={poolsPagination.total}
          current={poolsPagination.current}
          pageSize={poolsPagination.pageSize}
          onChange={handlePageChange}
          onDelete={() => {
            fetchStudentPools();
            fetchStatsData();
          }}
        />
      </div>
    </div>
  );
};

export default Home;
