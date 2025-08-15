import React, { useState, useEffect } from 'react';
import {
  Typography,
  Card,
  Table,
  message,
  Alert,
  Button,
  Space,
  Tag,
  Statistic,
  Row,
  Col
} from 'antd';
import {
  DollarOutlined,
  FileTextOutlined,
  PercentageOutlined,
  CalendarOutlined,
  ReloadOutlined,
  UserOutlined,
  PhoneOutlined
} from '@ant-design/icons';
import { useAuth } from '../../../hooks';
import { getAllStudentsDailyIncomeStats, type AllStudentsIncomeStatsResponse, type StudentIncomeStats } from '../../../api';
import styles from './index.module.css';

const { Title, Text } = Typography;

const StudentIncome: React.FC = () => {
  const { user, loading: authLoading } = useAuth();

  // 数据状态
  const [incomeData, setIncomeData] = useState<AllStudentsIncomeStatsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 分页状态
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // 获取所有学员收入统计数据
  const fetchIncomeStats = async (page: number = 1, size: number = 10) => {
    try {
      setLoading(true);
      setError(null);
      console.log('开始获取学员收入统计...');
      const response = await getAllStudentsDailyIncomeStats({ page, size });
      console.log('API响应:', response);
      setIncomeData(response.data);
      setPagination({
        current: response.data.page,
        pageSize: response.data.size,
        total: response.data.total
      });
      message.success('收入统计获取成功');
    } catch (error: any) {
      console.error('API调用失败:', error);
      console.error('错误详情:', {
        response: error?.response,
        status: error?.response?.status,
        data: error?.response?.data
      });
      const errorMsg = error?.response?.data?.message || error?.message || '获取收入统计失败';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 页面加载时获取数据
  useEffect(() => {
    if (!authLoading && user) {
      fetchIncomeStats(1, 10);
    }
  }, [authLoading, user]);

  // 处理分页变化
  const handleTableChange = (page: number, pageSize: number) => {
    fetchIncomeStats(page, pageSize);
  };

  // 格式化金额
  const formatAmount = (amount: string | number) => {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    return isNaN(num) ? '0.00' : num.toFixed(2);
  };

  // 计算汇总统计
  const getSummaryStats = () => {
    if (!incomeData || !incomeData.students) {
      return {
        totalStudents: 0,
        totalIncome: 0,
        totalOrders: 0,
        totalActualIncome: 0
      };
    }

    return incomeData.students.reduce((acc, student) => {
      acc.totalStudents += 1;
      acc.totalIncome += parseFloat(student.yesterdayIncome) || 0;
      acc.totalOrders += student.yesterdayCompletedOrders || 0;
      acc.totalActualIncome += parseFloat(student.actualIncome) || 0;
      return acc;
    }, {
      totalStudents: 0,
      totalIncome: 0,
      totalOrders: 0,
      totalActualIncome: 0
    });
  };

  // 表格列配置 - 精确对齐上方统计卡片
  // 计算考虑间距的实际宽度：总宽度减去3个16px间距，再除以4
  const cardWidth = 'calc((100% - 48px) / 4)'; // (100% - 3*16px) / 4

  const columns = [
    {
      title: '学员信息',
      key: 'student_info',
      width: cardWidth,
      render: (_: any, record: StudentIncomeStats) => (
        <Space direction="vertical" size="small">
          <Space>
            <UserOutlined />
            <span>{record.studentName}</span>
          </Space>
          <Space>
            <PhoneOutlined />
            <span style={{ color: '#666', fontSize: '12px' }}>
              {record.phoneNumber || '未填写'}
            </span>
          </Space>
          <Space size="small">
            <Tag color="blue" size="small">ID: {record.studentId}</Tag>
            {record.commissionRate === 'N/A' ? (
              <Tag color="orange" size="small">虚拟任务</Tag>
            ) : (
              <Tag color="green" size="small">
                返佣: {(() => {
                  const rateNum = parseFloat(record.commissionRate);
                  if (isNaN(rateNum)) return '0.0';
                  const percentage = rateNum <= 1 ? (rateNum * 100).toFixed(1) : rateNum.toFixed(1);
                  return percentage;
                })()}%
              </Tag>
            )}
          </Space>
        </Space>
      ),
    },
    {
      title: '昨日佣金',
      dataIndex: 'yesterdayIncome',
      key: 'yesterdayIncome',
      width: cardWidth,
      align: 'center' as const,
      render: (amount: string) => (
        <span style={{ color: '#1890ff', fontWeight: 'bold' }}>
          ¥{formatAmount(amount)}
        </span>
      ),
      sorter: (a: StudentIncomeStats, b: StudentIncomeStats) =>
        parseFloat(a.yesterdayIncome) - parseFloat(b.yesterdayIncome),
    },
    {
      title: '完成订单',
      dataIndex: 'yesterdayCompletedOrders',
      key: 'yesterdayCompletedOrders',
      width: cardWidth,
      align: 'center' as const,
      render: (count: number) => (
        <Tag color={count > 0 ? 'green' : 'default'}>
          {count || 0} 单
        </Tag>
      ),
      sorter: (a: StudentIncomeStats, b: StudentIncomeStats) =>
        a.yesterdayCompletedOrders - b.yesterdayCompletedOrders,
    },
    {
      title: '实际到手',
      dataIndex: 'actualIncome',
      key: 'actualIncome',
      width: cardWidth,
      align: 'center' as const,
      render: (amount: string) => (
        <span style={{ color: '#f5222d', fontWeight: 'bold' }}>
          ¥{formatAmount(amount)}
        </span>
      ),
      sorter: (a: StudentIncomeStats, b: StudentIncomeStats) =>
        parseFloat(a.actualIncome) - parseFloat(b.actualIncome),
    },

  ];

  const summaryStats = getSummaryStats();

  if (authLoading) {
    return (
      <div className={styles.loadingContainer}>
        <div>加载中...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title level={2}>学员收入统计</Title>
        <Space>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={() => fetchIncomeStats(pagination.current, pagination.pageSize)}
            loading={loading}
          >
            刷新数据
          </Button>
        </Space>
      </div>

      {error && (
        <Alert
          message="获取数据失败"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={() => fetchIncomeStats(1, 10)}>
              重试
            </Button>
          }
        />
      )}
      {incomeData ? (
        <div className={styles.content}>
            {/* 汇总统计卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic
                    title="学员总数"
                    value={summaryStats.totalStudents}
                    prefix={<UserOutlined />}
                    suffix="人"
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>

              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic
                    title="总佣金"
                    value={formatAmount(summaryStats.totalIncome)}
                    prefix={<DollarOutlined />}
                    suffix="元"
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>

              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic
                    title="总订单数"
                    value={summaryStats.totalOrders}
                    prefix={<FileTextOutlined />}
                    suffix="单"
                    valueStyle={{ color: '#faad14' }}
                  />
                </Card>
              </Col>

              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic
                    title="总实际收入"
                    value={formatAmount(summaryStats.totalActualIncome)}
                    prefix={<DollarOutlined />}
                    suffix="元"
                    valueStyle={{ color: '#f5222d' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* 学员收入列表 */}
            <Card
              title={
                <Space>
                  <CalendarOutlined />
                  <span>学员收入明细 ({incomeData.statDate})</span>
                </Space>
              }
            >
              <Table
                columns={columns}
                dataSource={incomeData.students}
                rowKey="studentId"
                pagination={{
                  current: pagination.current,
                  pageSize: pagination.pageSize,
                  total: pagination.total,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) =>
                    `第 ${range[0]}-${range[1]} 条/共 ${total} 条`,
                  pageSizeOptions: ['10', '20', '50', '100'],
                  locale: {
                    items_per_page: '/页',
                    jump_to: '跳至',
                    jump_to_confirm: '确定',
                    page: '页'
                  },
                  onChange: handleTableChange,
                  onShowSizeChange: handleTableChange,
                }}
                size="middle"
              />
            </Card>

            {/* 说明信息 */}
            <Card title="统计说明" style={{ marginTop: 16 }}>
              <div className={styles.description}>
                <p>
                  <Text strong>统计时间：</Text>
                  {incomeData.statDate} 00:00:00 - 23:59:59
                </p>
                <p>
                  <Text strong>计算规则：</Text>
                  实际到手金额 = 昨日佣金 × 返佣比例
                </p>
                <p>
                  <Text strong>完成标准：</Text>
                  任务状态为"已完成"且学员参与了该任务的执行
                </p>
              </div>
            </Card>
          </div>
        ) : (
          !loading && !error && (
            <Card>
              <div className={styles.emptyState}>
                <CalendarOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                <p>暂无收入数据</p>
                <Button type="primary" onClick={() => fetchIncomeStats(1, 10)}>
                  获取数据
                </Button>
              </div>
            </Card>
          )
        )}
    </div>
  );
};

export default StudentIncome;
