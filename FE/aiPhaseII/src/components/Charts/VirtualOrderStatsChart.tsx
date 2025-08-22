import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Row, Col, Statistic } from 'antd';
import { 
  UserOutlined, 
  DollarOutlined, 
  FileTextOutlined, 
  CheckCircleOutlined,
  TrophyOutlined,
  CrownOutlined
} from '@ant-design/icons';
import type { VirtualOrderStats } from '../../api/virtualOrders/types';

interface VirtualOrderStatsChartProps {
  data: VirtualOrderStats;
  loading?: boolean;
  isDailyStats?: boolean; // 新增：标识是否为每日统计
}

const VirtualOrderStatsChart: React.FC<VirtualOrderStatsChartProps> = ({ 
  data, 
  loading = false,
  isDailyStats = false
}) => {
  // 饼图配置 - 任务完成情况
  const pieOption = {
    title: {
      text: isDailyStats ? '今日任务完成情况' : '任务完成情况',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      bottom: 20
    },
    series: [
      {
        name: '任务状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '55%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          {
            value: data.totalTasksCompleted,
            name: '已完成任务',
            itemStyle: { color: '#52c41a' }
          },
          {
            value: data.totalTasksGenerated - data.totalTasksCompleted,
            name: '未完成任务',
            itemStyle: { color: '#ff7875' }
          }
        ]
      }
    ]
  };

  // 柱状图配置 - 统计概览
  const barOption = {
    title: {
      text: isDailyStats ? '今日数据统计概览' : '数据统计概览',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: isDailyStats ? ['活跃学生', '生成任务', '完成任务'] : ['学生总数', '生成任务', '完成任务'],
      axisLabel: {
        interval: 0,
        rotate: 0
      }
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '数量',
        type: 'bar',
        data: [
          {
            value: data.totalStudents,
            itemStyle: { color: '#1890ff' }
          },
          {
            value: data.totalTasksGenerated,
            itemStyle: { color: '#722ed1' }
          },
          {
            value: data.totalTasksCompleted,
            itemStyle: { color: '#52c41a' }
          }
        ],
        barWidth: '60%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card>
            <Statistic
              title={isDailyStats ? "今日活跃学生" : "学生总数"}
              value={data.totalStudents}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card>
            <Statistic
              title={isDailyStats ? "今日补贴金额" : "总补贴金额"}
              value={data.totalSubsidy}
              prefix={<DollarOutlined />}
              precision={2}
              valueStyle={{ color: '#52c41a' }}
              suffix="元"
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card>
            <Statistic
              title={isDailyStats ? "今日生成任务" : "生成任务数"}
              value={data.totalTasksGenerated}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card>
            <Statistic
              title={isDailyStats ? "今日完成率" : "完成率"}
              value={data.completionRate}
              prefix={<CheckCircleOutlined />}
              precision={2}
              valueStyle={{ color: '#fa8c16' }}
              suffix="%"
            />
          </Card>
        </Col>
        {/* 新增奖金池相关卡片 */}
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card>
            <Statistic
              title="奖池累计金额"
              value={data.bonusPoolTotal || 0}
              prefix={<TrophyOutlined />}
              precision={2}
              valueStyle={{ color: '#13c2c2' }}
              suffix="元"
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card>
            <Statistic
              title="可抢奖金池人数"
              value={data.qualifiedStudentsCount || 0}
              prefix={<CrownOutlined />}
              valueStyle={{ color: '#eb2f96' }}
              suffix="人"
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts 
              option={barOption} 
              style={{ height: '300px' }}
              showLoading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts 
              option={pieOption} 
              style={{ height: '300px' }}
              showLoading={loading}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default VirtualOrderStatsChart;
