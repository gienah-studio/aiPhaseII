import React, { useState } from 'react';
import {
  Table,
  Image,
  Tag,
  Space,
  Button,
  Popconfirm,
  Checkbox,
  Typography,
  Tooltip
} from 'antd';
import {
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  DownloadOutlined,
  TagsOutlined
} from '@ant-design/icons';
import type { ColumnsType, TableProps } from 'antd/es/table';
import styles from './index.module.css';

const { Text } = Typography;

export interface ResourceItem {
  id: string;
  fileName: string;
  thumbnail: string;
  category: string;
  fileSize: string;
  dimensions: string;
  status: 'available' | 'used' | 'disabled';
  uploadTime: string;
}

interface ResourceTableProps {
  data: ResourceItem[];
  loading?: boolean;
  selectedRowKeys: string[];
  onSelectionChange: (selectedRowKeys: string[]) => void;
  onView: (record: ResourceItem) => void;
  onDelete: (record: ResourceItem) => void;
  pagination?: {
    current: number;
    pageSize: number;
    total: number;
    showSizeChanger?: boolean;
    showQuickJumper?: boolean;
    showTotal?: (total: number, range: [number, number]) => string;
    pageSizeOptions?: string[];
  };
  onTableChange?: (page: number, pageSize?: number) => void;
}

const ResourceTable: React.FC<ResourceTableProps> = ({
  data,
  loading,
  selectedRowKeys,
  onSelectionChange,
  onView,
  onDelete,
  pagination,
  onTableChange
}) => {
  const getStatusConfig = (status: ResourceItem['status']) => {
    const configs = {
      available: { color: 'success', text: '可用' },
      used: { color: 'processing', text: '已使用' },
      disabled: { color: 'default', text: '已禁用' }
    };
    return configs[status] || { color: 'default', text: '未知' };
  };

  const columns: ColumnsType<ResourceItem> = [
    {
      title: '序号',
      key: 'index',
      width: 60,
      render: (_, __, index) => index + 1,
      fixed: 'left'
    },
    {
      title: '缩略图',
      dataIndex: 'thumbnail',
      key: 'thumbnail',
      width: 80,
      render: (thumbnail: string, record) => (
        <Image
          src={thumbnail}
          alt={record.fileName}
          width={60}
          height={60}
          className={styles.thumbnail}
          fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3Ik1RnG4W+FgYxYQQ=="
          preview={{
            mask: <EyeOutlined />
          }}
        />
      ),
      fixed: 'left'
    },
    {
      title: '文件名',
      dataIndex: 'fileName',
      key: 'fileName',
      width: 200,
      ellipsis: {
        showTitle: false
      },
      render: (fileName: string) => (
        <Tooltip title={fileName}>
          <Text strong className={styles.fileName}>
            {fileName}
          </Text>
        </Tooltip>
      )
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => (
        <Tag color="blue">{category}</Tag>
      )
    },
    {
      title: '文件大小',
      dataIndex: 'fileSize',
      key: 'fileSize',
      width: 100,
      sorter: (a, b) => {
        const aSize = parseFloat(a.fileSize);
        const bSize = parseFloat(b.fileSize);
        return aSize - bSize;
      }
    },
    {
      title: '图片尺寸',
      dataIndex: 'dimensions',
      key: 'dimensions',
      width: 120
    },
    {
      title: '使用状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ResourceItem['status']) => {
        const config = getStatusConfig(status);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
      filters: [
        { text: '可用', value: 'available' },
        { text: '已使用', value: 'used' },
        { text: '已禁用', value: 'disabled' }
      ],
      onFilter: (value, record) => record.status === value
    },
    {
      title: '上传时间',
      dataIndex: 'uploadTime',
      key: 'uploadTime',
      width: 160,
      sorter: (a, b) => new Date(a.uploadTime).getTime() - new Date(b.uploadTime).getTime()
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => onView(record)}
              size="small"
            />
          </Tooltip>
          <Popconfirm
            title="确定删除这个资源吗？"
            description="删除后无法恢复，请确认操作。"
            onConfirm={() => onDelete(record)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button
                type="text"
                icon={<DeleteOutlined />}
                danger
                size="small"
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  const rowSelection: TableProps<ResourceItem>['rowSelection'] = {
    selectedRowKeys,
    onChange: onSelectionChange,
    getCheckboxProps: (record) => ({
      disabled: record.status === 'disabled'
    })
  };

  return (
    <Table<ResourceItem>
      columns={columns}
      dataSource={data}
      rowKey="id"
      loading={loading}
      rowSelection={rowSelection}
      scroll={{ x: 1400, y: 600 }}
      pagination={pagination ? {
        ...pagination,
        onChange: onTableChange,
        onShowSizeChange: onTableChange
      } : {
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, range) =>
          `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        pageSizeOptions: ['10', '20', '50', '100']
      }}
      className={styles.resourceTable}
      size="middle"
    />
  );
};

export default ResourceTable;