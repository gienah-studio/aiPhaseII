import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Button,
  DatePicker,
  Space,
  message,
  Statistic,
  Row,
  Col,
  InputNumber,
  Tooltip
} from 'antd';
import { DownloadOutlined, ReloadOutlined, CalendarOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  getDailySubsidyStats,
  exportDailySubsidyStats,
  type DailySubsidyStats,
  type DailySubsidyStatsParams
} from '../../api';
import styles from './index.module.css';

const { RangePicker } = DatePicker;

interface DailySubsidyStatsTableProps {
  className?: string;
}

const DailySubsidyStatsTable: React.FC<DailySubsidyStatsTableProps> = ({ className }) => {
  const [data, setData] = useState<DailySubsidyStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [queryParams, setQueryParams] = useState<DailySubsidyStatsParams>({
    days: 7
  });

  // 获取数据
  const fetchData = async (params?: DailySubsidyStatsParams) => {
    try {
      setLoading(true);
      const result = await getDailySubsidyStats(params || queryParams);
      setData(result);
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '获取数据失败';
      message.error(errorMsg);
      console.error('获取每日补贴统计数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 导出数据
  const handleExport = async () => {
    try {
      setExportLoading(true);
      console.log('开始导出，参数:', queryParams);
      const blob = await exportDailySubsidyStats(queryParams);

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
      
      // 生成文件名
      const timestamp = new Date().toISOString().split('T')[0];
      let filename = `每日补贴统计_${timestamp}.xlsx`;
      if (queryParams.startDate && queryParams.endDate) {
        filename = `每日补贴统计_${queryParams.startDate}_${queryParams.endDate}.xlsx`;
      } else if (queryParams.days) {
        filename = `每日补贴统计_最近${queryParams.days}天_${timestamp}.xlsx`;
      }
      
      link.download = filename;
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
    } finally {
      setExportLoading(false);
    }
  };

  // 处理日期范围变化
  const handleDateRangeChange = (dates: any) => {
    if (dates && dates.length === 2) {
      const newParams = {
        startDate: dates[0].format('YYYY-MM-DD'),
        endDate: dates[1].format('YYYY-MM-DD')
      };
      setQueryParams(newParams);
      fetchData(newParams);
    } else {
      // 清空日期范围，使用天数查询
      const newParams = { days: queryParams.days || 7 };
      setQueryParams(newParams);
      fetchData(newParams);
    }
  };

  // 处理天数变化
  const handleDaysChange = (value: number | null) => {
    if (value && value > 0) {
      const newParams = { days: value };
      setQueryParams(newParams);
      fetchData(newParams);
    }
  };

  // 刷新数据
  const handleRefresh = () => {
    fetchData();
  };

  // 表格列定义
  const columns: ColumnsType<any> = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      fixed: 'left',
      render: (date: string) => {
        const dateObj = dayjs(date);
        const today = dayjs();
        const yesterday = today.subtract(1, 'day');

        if (dateObj.isSame(today, 'day')) {
          return <span style={{ color: '#52c41a', fontWeight: 'bold' }}>今天</span>;
        } else if (dateObj.isSame(yesterday, 'day')) {
          return <span style={{ color: '#1890ff', fontWeight: 'bold' }}>昨天</span>;
        } else {
          return dateObj.format('MM-DD');
        }
      }
    },
    {
      title: '补贴总金额',
      dataIndex: 'subsidyTotalAmount',
      key: 'subsidyTotalAmount',
      width: 120,
      render: (value: number) => `¥${value.toFixed(2)}`
    },
    {
      title: '实际获得金额',
      dataIndex: 'actualEarnedAmount',
      key: 'actualEarnedAmount',
      width: 130,
      render: (value: number) => `¥${value.toFixed(2)}`
    },
    {
      title: '完成率',
      dataIndex: 'completionRate',
      key: 'completionRate',
      width: 100,
      render: (value: number) => `${value.toFixed(1)}%`
    },
    {
      title: '生成任务数',
      dataIndex: 'tasksGenerated',
      key: 'tasksGenerated',
      width: 110
    },
    {
      title: '完成任务数',
      dataIndex: 'tasksCompleted',
      key: 'tasksCompleted',
      width: 110
    },
    {
      title: '剩余金额',
      dataIndex: 'remainingAmount',
      key: 'remainingAmount',
      width: 120,
      render: (value: number) => `¥${value.toFixed(2)}`
    },
    {
      title: '补贴学员数',
      dataIndex: 'activeStudentsCount',
      key: 'activeStudentsCount',
      width: 110,
      render: (value: number) => value || 0
    },
    {
      title: '达标学生数',
      dataIndex: ['achievementStats', 'achievedStudents'],
      key: 'achievedStudents',
      width: 110
    }
  ];

  // 组件挂载时获取数据
  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className={`${styles.container} ${className}`}>
      <Card
        title="每日补贴统计"
        extra={
          <Space>
            <Tooltip title="查询天数">
              <InputNumber
                min={1}
                max={30}
                value={queryParams.days}
                onChange={handleDaysChange}
                disabled={!!(queryParams.startDate && queryParams.endDate)}
                addonBefore={<CalendarOutlined />}
                addonAfter="天"
                style={{ width: 120 }}
              />
            </Tooltip>
            <RangePicker
              value={queryParams.startDate && queryParams.endDate ? [
                dayjs(queryParams.startDate),
                dayjs(queryParams.endDate)
              ] : null}
              onChange={handleDateRangeChange}
              format="YYYY-MM-DD"
              placeholder={['开始日期', '结束日期']}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={loading}
              title="刷新数据"
            />
            <Tooltip title="导出Excel文件，包含每日统计、汇总统计和字段说明三个工作表">
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={handleExport}
                loading={exportLoading}
              >
                导出Excel
              </Button>
            </Tooltip>
          </Space>
        }
      >
        {/* 汇总统计 */}
        {data?.summary && (
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={4}>
              <Statistic
                title="总补贴金额"
                value={data.summary.totalSubsidyAmount}
                precision={2}
                prefix="¥"
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="总获得金额"
                value={data.summary.totalEarnedAmount}
                precision={2}
                prefix="¥"
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="总生成任务"
                value={data.summary.totalTasksGenerated}
                suffix="个"
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="总完成任务"
                value={data.summary.totalTasksCompleted}
                suffix="个"
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="整体完成率"
                value={data.summary.overallCompletionRate}
                precision={1}
                suffix="%"
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="统计天数"
                value={data.dateRange.days}
                suffix="天"
              />
            </Col>
          </Row>
        )}

        {/* 数据表格 */}
        <Table
          columns={columns}
          dataSource={data?.dailyStats || []}
          loading={loading}
          rowKey="date"
          pagination={false}
          scroll={{ x: 1000 }}
          size="small"
        />
      </Card>
    </div>
  );
};

export default DailySubsidyStatsTable;
