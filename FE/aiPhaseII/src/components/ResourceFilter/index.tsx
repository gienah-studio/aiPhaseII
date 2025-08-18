import React, { useState } from 'react';
import {
  Space,
  Input,
  Select,
  DatePicker,
  Button,
  Typography,
  Tag,
  Card,
  Checkbox
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  DownloadOutlined,
  DeleteOutlined,
  FolderOpenOutlined
} from '@ant-design/icons';
import styles from './index.module.css';

const { RangePicker } = DatePicker;
const { Text } = Typography;
// const { Option } = Select;

export interface FilterValues {
  keyword?: string;
  category?: string;
  status?: string;
  dateRange?: [string, string];
  fileSize?: string;
  uploadBatch?: string;
}

interface ResourceFilterProps {
  onFilterChange: (filters: FilterValues) => void;
  onReset: () => void;
  categories: Array<{ label: string; value: string }>;
  uploadBatches: Array<{ label: string; value: string }>;
  selectedCount: number;
  onBatchDownload: () => void;
  onBatchMove: () => void;
  onBatchStatusChange: () => void;
  onBatchDelete: () => void;
}

const ResourceFilter: React.FC<ResourceFilterProps> = ({
  onFilterChange,
  onReset,
  categories,
  uploadBatches,
  selectedCount,
  onBatchDownload,
  onBatchMove,
  onBatchStatusChange,
  onBatchDelete
}) => {
  const [filters, setFilters] = useState<FilterValues>({});

  const handleFilterChange = (key: keyof FilterValues, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleReset = () => {
    setFilters({});
    onReset();
  };

  const handleSearch = () => {
    onFilterChange(filters);
  };

  const statusOptions = [
    { label: '可用', value: 'available' },
    { label: '已使用', value: 'used' },
    { label: '已禁用', value: 'disabled' }
  ];

  return (
    <div className={styles.resourceFilter}>
      {/* 主搜索区域 */}
      <Card className={styles.searchCard}>
        <div className={styles.searchArea}>
          <Space wrap size="middle">
            <Input.Search
              placeholder="搜索文件名、图片编号"
              style={{ width: 200 }}
              value={filters.keyword}
              onChange={(e) => handleFilterChange('keyword', e.target.value)}
              onSearch={handleSearch}
              allowClear
            />
            <Select
              placeholder="选择分类"
              style={{ width: 150 }}
              value={filters.category}
              onChange={(value) => handleFilterChange('category', value)}
              allowClear
              options={categories}
            />
            <Select
              placeholder="使用状态"
              style={{ width: 120 }}
              value={filters.status}
              onChange={(value) => handleFilterChange('status', value)}
              allowClear
              options={statusOptions}
            />
            <RangePicker
              placeholder={['开始日期', '结束日期']}
              style={{ width: 240 }}
              onChange={(dates, dateStrings) =>
                handleFilterChange('dateRange', dateStrings)
              }
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSearch}
            >
              搜索
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
            >
              重置
            </Button>
          </Space>
        </div>

      </Card>

      {/* 批量操作区域 */}
      {selectedCount > 0 && (
        <Card className={styles.batchActionsCard}>
          <div className={styles.batchActions}>
            <div className={styles.selectionInfo}>
              <Checkbox
                indeterminate={selectedCount > 0}
                disabled
              >
                已选择 <strong>{selectedCount}</strong> 项
              </Checkbox>
            </div>

            <Space>
              <Button
                icon={<DownloadOutlined />}
                onClick={onBatchDownload}
                size="small"
              >
                批量下载
              </Button>
              <Button
                icon={<FolderOpenOutlined />}
                onClick={onBatchMove}
                size="small"
              >
                移动分类
              </Button>
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={onBatchDelete}
                size="small"
              >
                批量删除
              </Button>
            </Space>
          </div>
        </Card>
      )}

      {/* 当前筛选条件展示 */}
      {Object.keys(filters).length > 0 && (
        <div className={styles.activeFilters}>
          <Space wrap>
            <Text type="secondary">当前筛选条件：</Text>
            {filters.keyword && (
              <Tag closable onClose={() => handleFilterChange('keyword', undefined)}>
                关键词: {filters.keyword}
              </Tag>
            )}
            {filters.category && (
              <Tag closable onClose={() => handleFilterChange('category', undefined)}>
                分类: {categories.find(c => c.value === filters.category)?.label}
              </Tag>
            )}
            {filters.status && (
              <Tag closable onClose={() => handleFilterChange('status', undefined)}>
                状态: {statusOptions.find(s => s.value === filters.status)?.label}
              </Tag>
            )}
            {filters.dateRange && (
              <Tag closable onClose={() => handleFilterChange('dateRange', undefined)}>
                时间: {filters.dateRange[0]} ~ {filters.dateRange[1]}
              </Tag>
            )}
            <Button
              type="link"
              size="small"
              onClick={handleReset}
              style={{ padding: 0, height: 'auto' }}
            >
              清除全部
            </Button>
          </Space>
        </div>
      )}
    </div>
  );
};

export default ResourceFilter;