import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Button,
  Space,
  Select,
  DatePicker,
  message,
  Popconfirm,
  Tag,
  Typography,
  Divider,
  Upload,
  Modal,
  Spin,
  Progress
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  DownloadOutlined,
  TeamOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  UploadOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import {
  getStudentPools,
  getStudentIncomeSummary,
  reallocateStudentTasks,
  exportStudentIncome,
  importStudentSubsidy,
  deleteStudentPool,
  type StudentPoolItem,
  type StudentPoolParams,
  type StudentIncomeSummaryResponse,
  type StudentIncomeSummaryParams,
  type StudentSubsidyImportResponse
} from '../../../api';
import styles from './index.module.css';

const { Title } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

const StudentModule: React.FC = () => {
  // 数据状态
  const [poolData, setPoolData] = useState<StudentPoolItem[]>([]);
  const [summaryData, setSummaryData] = useState<StudentIncomeSummaryResponse | null>(null);
  const [poolLoading, setPoolLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // 搜索状态
  const [searchParams, setSearchParams] = useState<StudentPoolParams>({});
  const [summaryParams, setSummaryParams] = useState<StudentIncomeSummaryParams>({});

  // 导入相关状态
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importResult, setImportResult] = useState<StudentSubsidyImportResponse | null>(null);

  // 获取学生补贴池数据
  const fetchPoolData = async (params?: StudentPoolParams) => {
    try {
      setPoolLoading(true);
      const queryParams = {
        page: pagination.current,
        size: pagination.pageSize,
        ...searchParams,
        ...params
      };

      const response = await getStudentPools(queryParams);

      // 验证响应数据结构
      if (response && typeof response === 'object' && Array.isArray(response.items)) {
        setPoolData(response.items);
        setPagination(prev => ({
          ...prev,
          total: response.total || 0,
          current: response.page || queryParams.page,
          pageSize: response.size || queryParams.size
        }));
      } else {
        console.error('学生补贴池数据格式异常:', response);
        message.error('学生补贴池数据格式异常');
        setPoolData([]);
        setPagination(prev => ({
          ...prev,
          total: 0,
          current: queryParams.page,
          pageSize: queryParams.size
        }));
      }
    } catch (error) {
      message.error('获取学生补贴池数据失败');
      console.error('获取学生补贴池数据失败:', error);
      // 设置空数据以避免界面错误
      setPoolData([]);
      setPagination(prev => ({
        ...prev,
        total: 0
      }));
    } finally {
      setPoolLoading(false);
    }
  };

  // 获取学生收入汇总数据
  const fetchSummaryData = async (params?: StudentIncomeSummaryParams) => {
    try {
      setSummaryLoading(true);
      const response = await getStudentIncomeSummary({ ...summaryParams, ...params });

      // 验证响应数据结构
      if (response && typeof response === 'object') {
        setSummaryData(response);
      } else {
        console.error('学生收入汇总数据格式异常:', response);
        message.error('学生收入汇总数据格式异常');
        setSummaryData(null);
      }
    } catch (error) {
      message.error('获取学生收入汇总失败');
      console.error('获取学生收入汇总失败:', error);
      setSummaryData(null);
    } finally {
      setSummaryLoading(false);
    }
  };

  // 初始化数据
  useEffect(() => {
    fetchPoolData();
    fetchSummaryData();
  }, []);

  // 搜索处理
  const handleSearch = () => {
    setPagination(prev => ({ ...prev, current: 1 }));
    fetchPoolData({ page: 1 });
  };

  // 重置搜索
  const handleReset = () => {
    setSearchParams({});
    setPagination(prev => ({ ...prev, current: 1 }));
    fetchPoolData({ page: 1 });
  };

  // 分页处理
  const handleTableChange = (page: number, pageSize: number) => {
    setPagination(prev => ({ ...prev, current: page, pageSize }));
    fetchPoolData({ page, size: pageSize });
  };

  // 重新分配学生任务
  const handleReallocate = async (studentId: number) => {
    try {
      await reallocateStudentTasks(studentId);
      message.success('重新分配任务成功');
      fetchPoolData();
    } catch (error) {
      message.error('重新分配任务失败');
      console.error('重新分配任务失败:', error);
    }
  };

  // 删除学生补贴池
  const handleDeletePool = async (poolId: number) => {
    try {
      await deleteStudentPool(poolId);
      message.success('删除学生补贴池成功');
      fetchPoolData();
      fetchSummaryData();
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '删除失败';
      message.error(errorMsg);
      console.error('删除学生补贴池失败:', error);
    }
  };

  // 导出学生收入数据
  const handleExport = async () => {
    try {
      console.log('开始导出，参数:', summaryParams);
      const blob = await exportStudentIncome(summaryParams);

      // 检查返回的数据是否为有效的 Blob
      if (!(blob instanceof Blob)) {
        console.error('返回的数据不是 Blob 类型:', blob);
        message.error('导出数据格式错误');
        return;
      }

      console.log('获取到 Blob 数据，大小:', blob.size, '类型:', blob.type);

      // 检查 Blob 是否为空
      if (blob.size === 0) {
        message.error('导出的文件为空');
        return;
      }

      // 创建下载链接并触发下载
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `学生收入数据_${new Date().toISOString().split('T')[0]}.xlsx`;
      link.style.display = 'none';

      document.body.appendChild(link);
      link.click();

      // 清理资源
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);

      message.success('导出成功');
    } catch (error) {
      console.error('导出失败:', error);

      // 处理错误响应
      if ((error as any)?.response?.data instanceof Blob) {
        try {
          const text = await (error as any).response.data.text();
          const errorData = JSON.parse(text);
          message.error(`导出失败: ${errorData.detail || errorData.message || '服务器错误'}`);
        } catch {
          message.error('导出失败，服务器返回了无效的错误信息');
        }
      } else {
        const errorMsg = (error as any)?.response?.data?.detail || (error as any)?.response?.data?.message || (error as any)?.message || '网络错误';
        message.error(`导出失败: ${errorMsg}`);
      }
    }
  };

  // 日期范围变化处理
  const handleDateRangeChange = (dates: any) => {
    if (dates && dates.length === 2) {
      setSummaryParams({
        startDate: dates[0].format('YYYY-MM-DD'),
        endDate: dates[1].format('YYYY-MM-DD')
      });
    } else {
      setSummaryParams({});
    }
  };

  // 刷新汇总数据
  const handleRefreshSummary = () => {
    fetchSummaryData();
  };

  // 处理文件导入
  const handleImport = async (file: File) => {
    try {
      setImportLoading(true);
      const result = await importStudentSubsidy(file);
      setImportResult(result);

      message.success(`导入成功！导入 ${result.totalStudents} 名学生，总补贴 ${result.totalSubsidy} 元，生成 ${result.generatedTasks} 个虚拟任务`);

      // 导入成功后刷新数据
      fetchPoolData();
      fetchSummaryData();

      // 延迟关闭弹窗，让用户看到成功信息
      setTimeout(() => {
        setImportModalVisible(false);
        setImportResult(null);
      }, 3000);

      return true;
    } catch (error) {
      console.error('导入失败:', error);
      const errorMsg = (error as any)?.response?.data?.message || (error as any)?.message || '导入失败';
      message.error(errorMsg);
      return false;
    } finally {
      setImportLoading(false);
    }
  };

  // 打开导入弹窗
  const handleOpenImportModal = () => {
    setImportModalVisible(true);
    setImportResult(null);
  };

  // 关闭导入弹窗
  const handleCloseImportModal = () => {
    setImportModalVisible(false);
    setImportResult(null);
  };

  // 数据安全处理函数
  const safeNumber = (value: any): number => {
    if (typeof value === 'number' && !isNaN(value)) return value;
    if (typeof value === 'string' && !isNaN(Number(value))) return Number(value);
    return 0;
  };

  // 获取字段值（兼容新旧字段名）
  const getFieldValue = (record: StudentPoolItem, newField: string, oldField: string): any => {
    return record[newField as keyof StudentPoolItem] ?? record[oldField as keyof StudentPoolItem];
  };

  // 表格列配置
  const columns = [
    {
      title: '序号',
      key: 'index',
      width: 80,
      render: (_: any, __: any, index: number) => {
        return (pagination.current - 1) * pagination.pageSize + index + 1;
      },
    },
    {
      title: '学生姓名',
      key: 'student_name',
      width: 120,
      render: (_: any, record: StudentPoolItem) => getFieldValue(record, 'studentName', 'student_name') || '-'
    },
    {
      title: '补贴金额',
      key: 'subsidy_amount',
      width: 120,
      render: (_: any, record: StudentPoolItem) => {
        const amount = safeNumber(getFieldValue(record, 'totalSubsidy', 'subsidy_amount'));
        return `¥${amount.toFixed(2)}`;
      },
    },
    {
      title: '剩余金额',
      key: 'remaining_amount',
      width: 120,
      render: (_: any, record: StudentPoolItem) => {
        const amount = safeNumber(getFieldValue(record, 'remainingAmount', 'remaining_amount'));
        return (
          <span style={{ color: amount > 0 ? '#52c41a' : '#999' }}>
            ¥{amount.toFixed(2)}
          </span>
        );
      },
    },
    {
      title: '已分配金额',
      key: 'allocated_amount',
      width: 120,
      render: (_: any, record: StudentPoolItem) => {
        const amount = safeNumber(getFieldValue(record, 'allocatedAmount', 'tasks_generated'));
        return `¥${amount.toFixed(2)}`;
      },
    },
    {
      title: '已完成金额',
      key: 'completed_amount',
      width: 120,
      render: (_: any, record: StudentPoolItem) => {
        const amount = safeNumber(getFieldValue(record, 'completedAmount', 'tasks_completed'));
        return `¥${amount.toFixed(2)}`;
      },
    },
    {
      title: '完成率',
      key: 'completion_rate',
      width: 120,
      render: (_: any, record: StudentPoolItem) => {
        // 优先使用后端返回的完成率，如果没有则前端计算（兼容性）
        const backendRate = getFieldValue(record, 'completionRate', 'completion_rate');
        let rate = 0;

        if (backendRate !== undefined && backendRate !== null) {
          rate = safeNumber(backendRate);
        } else {
          // 兼容性：如果后端没有返回完成率，使用实际消耗的补贴来计算
          const totalSubsidy = safeNumber(getFieldValue(record, 'totalSubsidy', 'subsidy_amount'));
          const consumedSubsidy = safeNumber(getFieldValue(record, 'consumedSubsidy', 'consumed_subsidy'));
          rate = totalSubsidy > 0 ? (consumedSubsidy / totalSubsidy) * 100 : 0;
        }

        return (
          <Progress
            percent={Math.round(rate)}
            size="small"
            status={rate === 100 ? 'success' : 'active'}
          />
        );
      },
    },
    {
      title: '返佣比例',
      key: 'agent_rebate',
      width: 120,
      render: (_: any, record: StudentPoolItem) => {
        const rebate = getFieldValue(record, 'agentRebate', 'agent_rebate');
        return rebate ? `${rebate}%` : '-';
      },
    },
    {
      title: '实际获得金额',
      key: 'consumed_subsidy',
      width: 130,
      render: (_: any, record: StudentPoolItem) => {
        const amount = safeNumber(getFieldValue(record, 'consumedSubsidy', 'consumed_subsidy'));
        return (
          <span style={{ color: '#52c41a', fontWeight: 'bold' }}>
            ¥{amount.toFixed(2)}
          </span>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap = {
          'active': { color: 'green', text: '进行中' },
          'completed': { color: 'blue', text: '已完成' },
          'suspended': { color: 'orange', text: '暂停' },
          'expired': { color: 'red', text: '已过期' }
        };
        const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '导入批次',
      key: 'import_batch',
      width: 180,
      render: (_: any, record: StudentPoolItem) => getFieldValue(record, 'importBatch', 'import_batch') || '-'
    },
    {
      title: '创建时间',
      key: 'created_at',
      width: 180,
      render: (_: any, record: StudentPoolItem) => {
        const time = getFieldValue(record, 'createdAt', 'created_at');
        return time ? new Date(time).toLocaleString() : '-';
      },
    },
    // {
    //   title: '操作',
    //   key: 'action',
    //   width: 180,
    //   fixed: 'right' as const,
    //   render: (_: any, record: StudentPoolItem) => {
    //     const remainingAmount = safeNumber(getFieldValue(record, 'remainingAmount', 'remaining_amount'));
    //     const studentId = getFieldValue(record, 'studentId', 'student_id');
    //     const poolId = record.id;
    //
    //     return (
    //       <Space size="small">
    //         <Popconfirm
    //           title="确定要删除这个学生的补贴池吗？"
    //           description="删除后该学生的补贴记录将被软删除，如有未完成任务将无法删除。"
    //           onConfirm={() => handleDeletePool(Number(poolId))}
    //           okText="确定"
    //           cancelText="取消"
    //           okType="danger"
    //         >
    //           <Button
    //             type="link"
    //             size="small"
    //             icon={<DeleteOutlined />}
    //             danger
    //           >
    //             删除
    //           </Button>
    //         </Popconfirm>
    //       </Space>
    //     );
    //   },
    // },
  ];

  return (
    <div className={styles.container}>
      {/* 统计卡片 */}
      <div className={styles.statsSection}>
        <Row gutter={[24, 24]}>
          <Col xs={24} sm={12} md={12} lg={6} xl={6} xxl={6}>
            <Card className={styles.statCard}>
              <Statistic
                title="学生总数"
                value={summaryData?.totalStudents || 0}
                prefix={<TeamOutlined className={styles.statIcon} style={{ color: '#1890ff' }} />}
                loading={summaryLoading}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={12} lg={6} xl={6} xxl={6}>
            <Card className={styles.statCard}>
              <Statistic
                title="总金额"
                value={summaryData?.totalAmount || 0}
                precision={2}
                prefix={<DollarOutlined className={styles.statIcon} style={{ color: '#52c41a' }} />}
                suffix="元"
                loading={summaryLoading}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={12} lg={6} xl={6} xxl={6}>
            <Card className={styles.statCard}>
              <Statistic
                title="已完成任务"
                value={summaryData?.completedTasks || 0}
                prefix={<CheckCircleOutlined className={styles.statIcon} style={{ color: '#52c41a' }} />}
                loading={summaryLoading}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={12} lg={6} xl={6} xxl={6}>
            <Card className={styles.statCard}>
              <Statistic
                title="完成率"
                value={summaryData?.completionRate || 0}
                precision={1}
                prefix={<ClockCircleOutlined className={styles.statIcon} style={{ color: '#faad14' }} />}
                suffix="%"
                loading={summaryLoading}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
        </Row>
      </div>

      {/* 学生补贴池列表 */}
      <Card>
        <div className={styles.header}>
          <Title level={4}>学生补贴池管理</Title>

          {/* 汇总数据操作区域 */}
          <div className={styles.summaryArea}>
            <Space wrap>
              <RangePicker
                placeholder={['开始日期', '结束日期']}
                onChange={handleDateRangeChange}
              />
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleRefreshSummary}
                loading={summaryLoading}
              >
                查询汇总
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
              >
                导出数据
              </Button>
              <Button
                icon={<UploadOutlined />}
                onClick={handleOpenImportModal}
                type="default"
              >
                导入学生补贴
              </Button>
            </Space>
          </div>

          <Divider />

          {/* 搜索区域 */}
          <div className={styles.searchArea}>
            <Space wrap>
              <Select
                placeholder="选择状态"
                value={searchParams.status}
                onChange={(value) => setSearchParams(prev => ({ ...prev, status: value }))}
                style={{ width: 120 }}
                allowClear
              >
                <Option value="active">进行中</Option>
                <Option value="completed">已完成</Option>
                <Option value="suspended">暂停</Option>
                <Option value="expired">已过期</Option>
              </Select>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                搜索
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置
              </Button>
            </Space>
          </div>
        </div>

        {/* 表格 */}
        <Table
          columns={columns}
          dataSource={poolData}
          rowKey="id"
          loading={poolLoading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条/共 ${total} 条`,
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
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 导入学生补贴弹窗 */}
      <Modal
        title="导入学生补贴"
        open={importModalVisible}
        onCancel={handleCloseImportModal}
        footer={null}
        width={600}
      >
        <div style={{ padding: '20px 0' }}>
          <Upload.Dragger
            name="file"
            multiple={false}
            accept=".xlsx,.xls,.csv"
            beforeUpload={(file) => {
              handleImport(file);
              return false; // 阻止自动上传
            }}
            disabled={importLoading}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">
              支持 Excel (.xlsx, .xls) 和 CSV (.csv) 格式文件
              <br />
              上传后将自动导入学生补贴信息并生成虚拟任务
            </p>
          </Upload.Dragger>

          {importLoading && (
            <div style={{ textAlign: 'center', marginTop: '20px' }}>
              <Spin size="large" />
              <p style={{ marginTop: '10px', color: '#666' }}>正在导入数据，请稍候...</p>
            </div>
          )}

          {importResult && (
            <div style={{ marginTop: '20px', padding: '16px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: '6px' }}>
              <h4 style={{ color: '#52c41a', marginBottom: '12px' }}>导入成功！</h4>
              <p><strong>导入批次：</strong>{importResult.importBatch}</p>
              <p><strong>导入学生数：</strong>{importResult.totalStudents} 名</p>
              <p><strong>总补贴金额：</strong>¥{importResult.totalSubsidy}</p>
              <p><strong>生成任务数：</strong>{importResult.generatedTasks} 个</p>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default StudentModule;
