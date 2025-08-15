import React from 'react';
import { Table, Tag, Progress, Card, Typography, Button, Space, Popconfirm, message } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { StudentPoolItem } from '../../api/virtualOrders/types';
import { deleteStudentPool } from '../../api';

const { Title } = Typography;

interface StudentPoolTableProps {
  data: StudentPoolItem[];
  loading?: boolean;
  total?: number;
  current?: number;
  pageSize?: number;
  onChange?: (page: number, size?: number) => void;
  onDelete?: () => void; // 删除后的回调函数
}

const StudentPoolTable: React.FC<StudentPoolTableProps> = ({
  data,
  loading = false,
  total = 0,
  current = 1,
  pageSize = 10,
  onChange,
  onDelete
}) => {
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

  // 状态标签颜色映射
  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      'active': 'green',
      'completed': 'blue',
      'pending': 'orange',
      'inactive': 'red'
    };
    return colorMap[status] || 'default';
  };

  // 状态文本映射
  const getStatusText = (status: string) => {
    const textMap: Record<string, string> = {
      'active': '进行中',
      'completed': '已完成',
      'pending': '待处理',
      'inactive': '已停用'
    };
    return textMap[status] || status;
  };

  // 删除学生补贴池
  const handleDeletePool = async (poolId: number) => {
    try {
      await deleteStudentPool(poolId);
      message.success('删除学生补贴池成功');
      if (onDelete) {
        onDelete();
      }
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.message || '删除失败';
      message.error(errorMsg);
      console.error('删除学生补贴池失败:', error);
    }
  };

  const columns: ColumnsType<StudentPoolItem> = [
    {
      title: '序号',
      key: 'index',
      width: 80,
      fixed: 'left',
      render: (_, __, index) => {
        return (current - 1) * pageSize + index + 1;
      },
    },
    {
      title: '学生姓名',
      key: 'student_name',
      width: 120,
      render: (_, record) => getFieldValue(record, 'studentName', 'student_name') || '-'
    },
    {
      title: '补贴金额',
      key: 'subsidy_amount',
      width: 120,
      render: (_, record) => {
        const amount = safeNumber(getFieldValue(record, 'totalSubsidy', 'subsidy_amount'));
        return `¥${amount.toFixed(2)}`;
      },
      sorter: (a, b) => {
        const amountA = safeNumber(getFieldValue(a, 'totalSubsidy', 'subsidy_amount'));
        const amountB = safeNumber(getFieldValue(b, 'totalSubsidy', 'subsidy_amount'));
        return amountA - amountB;
      }
    },
    {
      title: '剩余金额',
      key: 'remaining_amount',
      width: 120,
      render: (_, record) => {
        const amount = safeNumber(getFieldValue(record, 'remainingAmount', 'remaining_amount'));
        return `¥${amount.toFixed(2)}`;
      },
      sorter: (a, b) => {
        const amountA = safeNumber(getFieldValue(a, 'remainingAmount', 'remaining_amount'));
        const amountB = safeNumber(getFieldValue(b, 'remainingAmount', 'remaining_amount'));
        return amountA - amountB;
      }
    },
    {
      title: '已分配金额',
      key: 'allocated_amount',
      width: 120,
      render: (_, record) => {
        const amount = safeNumber(getFieldValue(record, 'allocatedAmount', 'tasks_generated'));
        return `¥${amount.toFixed(2)}`;
      },
      sorter: (a, b) => {
        const amountA = safeNumber(getFieldValue(a, 'allocatedAmount', 'tasks_generated'));
        const amountB = safeNumber(getFieldValue(b, 'allocatedAmount', 'tasks_generated'));
        return amountA - amountB;
      }
    },
    {
      title: '已完成金额',
      key: 'completed_amount',
      width: 120,
      render: (_, record) => {
        const amount = safeNumber(getFieldValue(record, 'completedAmount', 'tasks_completed'));
        return `¥${amount.toFixed(2)}`;
      },
      sorter: (a, b) => {
        const amountA = safeNumber(getFieldValue(a, 'completedAmount', 'tasks_completed'));
        const amountB = safeNumber(getFieldValue(b, 'completedAmount', 'tasks_completed'));
        return amountA - amountB;
      }
    },
    {
      title: '完成率',
      key: 'completion_rate',
      width: 120,
      render: (_, record) => {
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
      sorter: (a, b) => {
        const totalSubsidyA = safeNumber(getFieldValue(a, 'totalSubsidy', 'subsidy_amount'));
        const completedAmountA = safeNumber(getFieldValue(a, 'completedAmount', 'tasks_completed'));
        const rateA = totalSubsidyA > 0 ? (completedAmountA / totalSubsidyA) * 100 : 0;

        const totalSubsidyB = safeNumber(getFieldValue(b, 'totalSubsidy', 'subsidy_amount'));
        const completedAmountB = safeNumber(getFieldValue(b, 'completedAmount', 'tasks_completed'));
        const rateB = totalSubsidyB > 0 ? (completedAmountB / totalSubsidyB) * 100 : 0;

        return rateA - rateB;
      }
    },
    {
      title: '返佣比例',
      key: 'agent_rebate',
      width: 120,
      render: (_, record) => {
        const rebate = getFieldValue(record, 'agentRebate', 'agent_rebate');
        return rebate ? `${rebate}%` : '-';
      },
      sorter: (a, b) => {
        const rebateA = parseFloat(getFieldValue(a, 'agentRebate', 'agent_rebate') || '0');
        const rebateB = parseFloat(getFieldValue(b, 'agentRebate', 'agent_rebate') || '0');
        return rebateA - rebateB;
      }
    },
    {
      title: '实际获得金额',
      key: 'consumed_subsidy',
      width: 130,
      render: (_, record) => {
        const amount = safeNumber(getFieldValue(record, 'consumedSubsidy', 'consumed_subsidy'));
        return (
          <span style={{ color: '#52c41a', fontWeight: 'bold' }}>
            ¥{amount.toFixed(2)}
          </span>
        );
      },
      sorter: (a, b) => {
        const amountA = safeNumber(getFieldValue(a, 'consumedSubsidy', 'consumed_subsidy'));
        const amountB = safeNumber(getFieldValue(b, 'consumedSubsidy', 'consumed_subsidy'));
        return amountA - amountB;
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      ),
      filters: [
        { text: '进行中', value: 'active' },
        { text: '已完成', value: 'completed' },
        { text: '待处理', value: 'pending' },
        { text: '已停用', value: 'inactive' }
      ],
      onFilter: (value, record) => record.status === value
    },
    {
      title: '导入批次',
      key: 'import_batch',
      width: 180,
      render: (_, record) => getFieldValue(record, 'importBatch', 'import_batch') || '-'
    },
    {
      title: '创建时间',
      key: 'created_at',
      width: 180,
      render: (_, record) => {
        const date = getFieldValue(record, 'createdAt', 'created_at');
        return date ? new Date(date).toLocaleString() : '-';
      },
      sorter: (a, b) => {
        const dateA = getFieldValue(a, 'createdAt', 'created_at');
        const dateB = getFieldValue(b, 'createdAt', 'created_at');
        if (!dateA || !dateB) return 0;
        return new Date(dateA).getTime() - new Date(dateB).getTime();
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Popconfirm
            title="确定要删除这个学生的补贴池吗？"
            description="删除后该学生的补贴记录将被软删除，如有未完成任务将无法删除。"
            onConfirm={() => handleDeletePool(Number(record.id))}
            okText="确定"
            cancelText="取消"
            okType="danger"
          >
            <Button
              type="link"
              size="small"
              icon={<DeleteOutlined />}
              danger
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <Card>
      <Title level={4} style={{ marginBottom: 16 }}>
        学生补贴池列表
      </Title>
      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        rowKey="id"
        scroll={{ x: 1000 }}
        pagination={{
          current,
          pageSize,
          total,
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
          onChange: onChange,
          onShowSizeChange: onChange
        }}
        size="middle"
      />
    </Card>
  );
};

export default StudentPoolTable;
