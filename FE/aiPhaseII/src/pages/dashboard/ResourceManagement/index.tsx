import React, { useState, useEffect, useRef } from 'react';
import { Layout, Card, Row, Col, Space, Button, Typography, message, Modal, Select, Tag, Image } from 'antd';
import {
  FolderOutlined,
  AppstoreOutlined,
  CloudUploadOutlined,
  DatabaseOutlined,
  TableOutlined,
  AppstoreAddOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import {
  ResourceTable,
  ResourceCards,
  ResourceFilter,
  ResourceUpload,
  CategoryManager
} from '../../../components';
import type { ResourceItem } from '../../../components/ResourceList/ResourceTable';
import type { CategoryNode } from '../../../components/CategoryManager';
import ResourceAPI, { CategoryAPI } from '../../../api/resources';
import type { FilterValues } from '../../../components/ResourceFilter';
import type { UploadFile } from 'antd';
import type { DetailedStatsResponse } from '../../../api/resources/types';
import styles from './index.module.css';

const { Content, Sider } = Layout;
const { Title, Text } = Typography;

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  onClick?: () => void;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, onClick }) => (
  <Card 
    className={`${styles.statCard} ${onClick ? styles.clickableCard : ''}`}
    onClick={onClick}
    hoverable={!!onClick}
  >
    <div className={styles.statContent}>
      <div className={styles.statIcon} style={{ color }}>
        {icon}
      </div>
      <div className={styles.statInfo}>
        <Text className={styles.statTitle}>{title}</Text>
        <div className={styles.statValue}>{value}</div>
      </div>
    </div>
  </Card>
);

const ResourceManagement: React.FC = () => {
  const [viewMode, setViewMode] = useState<'table' | 'card'>('table');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const hasLoadedRef = useRef(false);
  
  // 批量操作相关状态
  const [batchDeleteModalOpen, setBatchDeleteModalOpen] = useState(false);
  const [batchMoveModalOpen, setBatchMoveModalOpen] = useState(false);
  const [selectedTargetCategory, setSelectedTargetCategory] = useState<string>('');
  const [batchOperationLoading, setBatchOperationLoading] = useState(false);
  
  // 数据状态
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [statsData, setStatsData] = useState([
    {
      title: '资源总数',
      value: '0',
      icon: <FolderOutlined />,
      color: '#1890ff'
    },
    {
      title: '分类总数',
      value: '0',
      icon: <AppstoreOutlined />,
      color: '#52c41a'
    },
    {
      title: '今日上传',
      value: '0',
      icon: <CloudUploadOutlined />,
      color: '#faad14'
    },
    {
      title: '存储空间',
      value: '0 GB',
      icon: <DatabaseOutlined />,
      color: '#722ed1'
    }
  ]);

  // 数据映射函数
  const mapResourceData = (apiData: any[]): ResourceItem[] => {
    return apiData.map(item => ({
      id: item.id?.toString() || '',
      fileName: item.originalFilename || item.fileName || '未知文件',
      thumbnail: item.fileUrl || item.thumbnail || '',
      category: item.categoryName || item.category || '未分类',
      fileSize: item.fileSize ? `${(item.fileSize / 1024).toFixed(2)} KB` : '0 KB',
      dimensions: item.imageWidth && item.imageHeight 
        ? `${item.imageWidth} × ${item.imageHeight}` 
        : item.dimensions || '未知',
      status: item.usageStatus || item.status || 'available',
      uploadTime: item.createdAt || item.uploadTime || '未知时间'
    }));
  };

  // 加载数据
  useEffect(() => {
    if (!hasLoadedRef.current) {
      hasLoadedRef.current = true;
      loadInitialData();
    }
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [resourcesRes, categoriesRes, statsRes] = await Promise.allSettled([
        ResourceAPI.getResources(),
        CategoryAPI.getCategories(),
        ResourceAPI.getResourceStats()
      ]);

      if (resourcesRes.status === 'fulfilled') {
        const rawData = resourcesRes.value.data.items || [];
        setResources(mapResourceData(rawData));
      }

      if (categoriesRes.status === 'fulfilled') {
        // 处理分类接口返回的数据
        const categoriesData = categoriesRes.value.data.categories || [];
        let mappedCategories = categoriesData.map((category: any) => ({
          id: category.id.toString(),
          name: category.categoryName,
          description: category.description,
          resourceCount: 0, // 初始化为0，后面从统计接口更新
          children: []
        }));

        // 如果统计数据可用，更新分类的资源数量
        if (statsRes.status === 'fulfilled') {
          const stats = statsRes.value.data;
          const categoryStats = stats.categoriesStats || [];
          
          mappedCategories = mappedCategories.map(category => {
            const stat = categoryStats.find((s: any) => s.category_name === category.name);
            return {
              ...category,
              resourceCount: stat ? stat.total : 0
            };
          });
        }
        
        setCategories(mappedCategories);
      }

      if (statsRes.status === 'fulfilled') {
        const stats = statsRes.value.data;
        setStatsData([
          {
            title: '资源总数',
            value: (stats.totalImages || 0).toLocaleString(),
            icon: <FolderOutlined />,
            color: '#1890ff'
          },
          {
            title: '可用资源',
            value: (stats.availableImages || 0).toString(),
            icon: <AppstoreOutlined />,
            color: '#52c41a'
          },
          {
            title: '已使用',
            value: (stats.usedImages || 0).toString(),
            icon: <CloudUploadOutlined />,
            color: '#faad14'
          },
          {
            title: '可用率',
            value: stats.totalImages > 0 ? `${((stats.availableImages / stats.totalImages) * 100).toFixed(1)}%` : '0%',
            icon: <DatabaseOutlined />,
            color: '#722ed1'
          }
        ]);
      }
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理筛选
  const handleFilterChange = async (filters: FilterValues) => {
    setLoading(true);
    try {
      const params = {
        keyword: filters.keyword,
        categoryId: filters.category,
        status: filters.status as 'available' | 'used' | 'disabled' | undefined,
        startDate: filters.dateRange?.[0],
        endDate: filters.dateRange?.[1]
      };

      const response = await ResourceAPI.getResources(params);
      const rawData = response.data.items || [];
      setResources(mapResourceData(rawData));
    } catch (error) {
      message.error('筛选资源失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理资源上传
  const handleUpload = async (files: UploadFile[], formData: any) => {
    try {
      const uploadPromises = files.map(file => 
        ResourceAPI.uploadResource(file.originFileObj as File, {
          categoryId: formData.category,
          qualityScore: formData.qualityScore || 5,
          tags: formData.tags || [],
          description: formData.description
        })
      );

      await Promise.all(uploadPromises);
      message.success('上传成功');
      loadInitialData(); // 重新加载数据
    } catch (error) {
      throw error;
    }
  };

  // 处理批量上传
  const handleBatchUpload = async (file: UploadFile, formData: any) => {
    try {
      await ResourceAPI.uploadArchive(file.originFileObj as File, {
        categoryId: formData.category,
        qualityScore: formData.qualityScore || 5,
        tags: formData.tags || [],
        description: formData.description
      });
      loadInitialData(); // 重新加载数据
    } catch (error) {
      throw error;
    }
  };

  // 分类相关操作
  const handleCategorySelect = (categoryId: string) => {
    setSelectedCategory(categoryId);
    if (categoryId) {
      handleFilterChange({ category: categoryId });
    }
  };

  const handleCategoryAdd = async (category: Omit<CategoryNode, 'id' | 'resourceCount'>) => {
    await CategoryAPI.createCategory(category);
    loadInitialData();
  };

  const handleCategoryEdit = async (categoryId: string, category: Partial<CategoryNode>) => {
    await CategoryAPI.updateCategory(categoryId, category);
    loadInitialData();
  };

  const handleCategoryDelete = async (categoryId: string) => {
    await CategoryAPI.deleteCategory(categoryId);
    loadInitialData();
  };

  // 资源操作
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [currentResource, setCurrentResource] = useState<ResourceItem | null>(null);
  
  // 详细统计弹窗相关状态
  const [detailStatsModalVisible, setDetailStatsModalVisible] = useState(false);
  const [detailStatsData, setDetailStatsData] = useState<DetailedStatsResponse | null>(null);
  const [detailStatsLoading, setDetailStatsLoading] = useState(false);

  const handleResourceView = (record: ResourceItem) => {
    setCurrentResource(record);
    setViewModalVisible(true);
  };

  const handleResourceDelete = async (record: ResourceItem) => {
    try {
      await ResourceAPI.deleteResource(record.id);
      message.success('删除成功');
      loadInitialData();
    } catch (error) {
      message.error('删除失败');
    }
  };


  // 批量操作
  const handleBatchDownload = async () => {
    try {
      const blob = await ResourceAPI.downloadResources(selectedRowKeys);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'resources.zip';
      a.click();
      window.URL.revokeObjectURL(url);
      message.success('下载成功');
    } catch (error) {
      message.error('批量下载失败');
    }
  };


  // 显示批量移动分类对话框
  const handleBatchMove = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要移动的资源');
      return;
    }
    setBatchMoveModalOpen(true);
  };

  // 确认批量移动分类
  const handleConfirmBatchMove = async () => {
    if (!selectedTargetCategory) {
      message.warning('请选择目标分类');
      return;
    }

    setBatchOperationLoading(true);
    try {
      const response = await ResourceAPI.batchMoveCategoryResources(
        selectedRowKeys,
        selectedTargetCategory
      );
      
      // 根据实际的后端响应格式判断成功
      if (response.code === 200) {
        const { movedCount, skippedCount, targetCategory } = response.data;
        if (movedCount > 0) {
          message.success(`成功移动 ${movedCount} 个资源到 "${targetCategory.name}" 分类`);
        }
        if (skippedCount > 0) {
          message.info(`${skippedCount} 个资源已在目标分类中，已跳过`);
        }
      } else {
        message.error(response.msg || '批量移动失败');
      }
      
      setBatchMoveModalOpen(false);
      setSelectedTargetCategory('');
      setSelectedRowKeys([]);
      loadInitialData();
    } catch (error: any) {
      message.error(error?.response?.data?.msg || '批量移动失败');
    } finally {
      setBatchOperationLoading(false);
    }
  };

  const handleBatchStatusChange = () => {
    // TODO: 实现批量状态修改
    console.log('批量状态修改:', selectedRowKeys);
  };

  // 显示批量删除确认对话框
  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要删除的资源');
      return;
    }
    setBatchDeleteModalOpen(true);
  };

  // 确认批量删除
  const handleConfirmBatchDelete = async () => {
    setBatchOperationLoading(true);
    try {
      const response = await ResourceAPI.batchDeleteResources(selectedRowKeys);
      
      // 根据实际的后端响应格式判断成功
      if (response.code === 200) {
        const { deletedCount } = response.data;
        message.success(`成功删除 ${deletedCount} 个资源`);
      } else {
        message.error(response.msg || '批量删除失败');
      }
      
      setBatchDeleteModalOpen(false);
      setSelectedRowKeys([]);
      loadInitialData();
    } catch (error: any) {
      message.error(error?.response?.data?.msg || '批量删除失败');
    } finally {
      setBatchOperationLoading(false);
    }
  };

  // 处理统计卡片点击事件
  const handleStatsCardClick = async () => {
    setDetailStatsLoading(true);
    setDetailStatsModalVisible(true);
    
    try {
      const response = await ResourceAPI.getCategoryDetailedStats();
      if (response.code === 200) {
        setDetailStatsData(response.data);
      } else {
        message.error(response.msg || '获取详细统计失败');
      }
    } catch (error) {
      message.error('获取详细统计失败');
      console.error('Failed to fetch detailed stats:', error);
    } finally {
      setDetailStatsLoading(false);
    }
  };

  // 转换分类数据格式
  const categoryOptions = categories.map(category => ({
    label: category.name,
    value: category.id
  }));

  return (
    <div className={styles.resourceManagement}>
      <div className={styles.header}>
        <Title level={3} className={styles.pageTitle}>
          资源库管理
        </Title>
        <Space>
          <Button
            type={viewMode === 'table' ? 'primary' : 'default'}
            icon={<TableOutlined />}
            onClick={() => setViewMode('table')}
          >
            列表视图
          </Button>
          <Button
            type={viewMode === 'card' ? 'primary' : 'default'}
            icon={<AppstoreAddOutlined />}
            onClick={() => setViewMode('card')}
          >
            卡片视图
          </Button>
        </Space>
      </div>

      {/* 统计卡片区域 */}
      <Row gutter={[24, 24]} className={styles.statsRow}>
        {statsData.map((stat, index) => (
          <Col key={index} xs={24} sm={12} lg={6}>
            <StatCard {...stat} onClick={handleStatsCardClick} />
          </Col>
        ))}
      </Row>

      <Layout className={styles.contentLayout}>
        {/* 左侧分类管理 */}
        <Sider width={280} className={styles.sider}>
          <CategoryManager
            categories={categories}
            selectedCategory={selectedCategory}
            onCategorySelect={handleCategorySelect}
            onCategoryAdd={handleCategoryAdd}
            onCategoryEdit={handleCategoryEdit}
            onCategoryDelete={handleCategoryDelete}
            loading={loading}
          />
        </Sider>

        {/* 主内容区域 */}
        <Layout>
          <Content className={styles.mainContent}>
            {/* 搜索筛选区域 */}
            <ResourceFilter
              onFilterChange={handleFilterChange}
              onReset={() => {
                setSelectedCategory('');
                loadInitialData();
              }}
              categories={categoryOptions}
              uploadBatches={[]}
              selectedCount={selectedRowKeys.length}
              onBatchDownload={handleBatchDownload}
              onBatchMove={handleBatchMove}
              onBatchStatusChange={handleBatchStatusChange}
              onBatchDelete={handleBatchDelete}
            />

            {/* 资源上传区域 */}
            <ResourceUpload
              categories={categoryOptions}
              onUpload={handleUpload}
              onBatchUpload={handleBatchUpload}
            />

            {/* 资源列表区域 */}
            <Card title="资源列表" className={styles.listCard}>
              {viewMode === 'table' ? (
                <ResourceTable
                  data={resources}
                  loading={loading}
                  selectedRowKeys={selectedRowKeys}
                  onSelectionChange={setSelectedRowKeys}
                  onView={handleResourceView}
                  onDelete={handleResourceDelete}
                />
              ) : (
                <ResourceCards
                  data={resources}
                  loading={loading}
                  selectedRowKeys={selectedRowKeys}
                  onSelectionChange={setSelectedRowKeys}
                  onView={handleResourceView}
                  onDelete={handleResourceDelete}
                />
              )}
            </Card>
          </Content>
        </Layout>
      </Layout>

      {/* 批量删除确认对话框 */}
      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#faad14' }} />
            批量删除确认
          </Space>
        }
        open={batchDeleteModalOpen}
        onOk={handleConfirmBatchDelete}
        onCancel={() => setBatchDeleteModalOpen(false)}
        confirmLoading={batchOperationLoading}
        okText="确认删除"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <p>您确定要删除选中的 <strong>{selectedRowKeys.length}</strong> 个资源吗？</p>
        <p style={{ color: '#ff4d4f', marginBottom: 0 }}>
          此操作不可撤销，请谨慎操作！
        </p>
      </Modal>

      {/* 批量移动分类对话框 */}
      <Modal
        title="批量移动分类"
        open={batchMoveModalOpen}
        onOk={handleConfirmBatchMove}
        onCancel={() => {
          setBatchMoveModalOpen(false);
          setSelectedTargetCategory('');
        }}
        confirmLoading={batchOperationLoading}
        okText="确认移动"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <p>将选中的 <strong>{selectedRowKeys.length}</strong> 个资源移动到指定分类：</p>
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: 8 }}>选择目标分类：</label>
          <Select
            style={{ width: '100%' }}
            placeholder="请选择目标分类"
            value={selectedTargetCategory}
            onChange={setSelectedTargetCategory}
            options={categoryOptions}
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
          />
        </div>
      </Modal>

      {/* 资源详情查看弹窗 */}
      <Modal
        title="资源详情"
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false);
          setCurrentResource(null);
        }}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
        centered
      >
        {currentResource && (
          <div style={{ padding: '16px 0' }}>
            <Row gutter={24}>
              <Col span={12}>
                <Image
                  src={currentResource.thumbnail}
                  alt={currentResource.fileName}
                  style={{ width: '100%', borderRadius: 8 }}
                  fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3Ik1RnG4W+FgYxYQQ=="
                />
              </Col>
              <Col span={12}>
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  <div>
                    <Text strong>文件名：</Text>
                    <Text>{currentResource.fileName}</Text>
                  </div>
                  <div>
                    <Text strong>分类：</Text>
                    <Tag color="blue">{currentResource.category}</Tag>
                  </div>
                  <div>
                    <Text strong>文件大小：</Text>
                    <Text>{currentResource.fileSize}</Text>
                  </div>
                  <div>
                    <Text strong>图片尺寸：</Text>
                    <Text>{currentResource.dimensions}</Text>
                  </div>
                  <div>
                    <Text strong>使用状态：</Text>
                    <Tag color={currentResource.status === 'available' ? 'success' : currentResource.status === 'used' ? 'processing' : 'default'}>
                      {currentResource.status === 'available' ? '可用' : currentResource.status === 'used' ? '已使用' : '已禁用'}
                    </Tag>
                  </div>
                  <div>
                    <Text strong>上传时间：</Text>
                    <Text>{currentResource.uploadTime}</Text>
                  </div>
                </Space>
              </Col>
            </Row>
          </div>
        )}
      </Modal>

      {/* 详细统计弹窗 */}
      <Modal
        title="资源详细统计"
        open={detailStatsModalVisible}
        onCancel={() => {
          setDetailStatsModalVisible(false);
          setDetailStatsData(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailStatsModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={900}
        centered
      >
        {detailStatsLoading ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Text>正在加载详细统计数据...</Text>
          </div>
        ) : detailStatsData ? (
          <div style={{ padding: '16px 0' }}>
            {/* 总体统计 */}
            <div style={{ marginBottom: 32 }}>
              <Title level={4} style={{ marginBottom: 16 }}>总体统计</Title>
              <Row gutter={[16, 16]}>
                <Col span={6}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                      {(detailStatsData.avatarRedesign?.total || 0) + 
                       (detailStatsData.roomDecoration?.total || 0) + 
                       (detailStatsData.photoExtension?.total || 0)}
                    </div>
                    <div>资源总数</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                      {(detailStatsData.avatarRedesign?.available || 0) + 
                       (detailStatsData.roomDecoration?.available || 0) + 
                       (detailStatsData.photoExtension?.available || 0)}
                    </div>
                    <div>可用数量</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                      {(detailStatsData.avatarRedesign?.used || 0) + 
                       (detailStatsData.roomDecoration?.used || 0) + 
                       (detailStatsData.photoExtension?.used || 0)}
                    </div>
                    <div>已使用</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#722ed1' }}>
                      {(() => {
                        const totalCount = (detailStatsData.avatarRedesign?.total || 0) + 
                                         (detailStatsData.roomDecoration?.total || 0) + 
                                         (detailStatsData.photoExtension?.total || 0);
                        const availableCount = (detailStatsData.avatarRedesign?.available || 0) + 
                                              (detailStatsData.roomDecoration?.available || 0) + 
                                              (detailStatsData.photoExtension?.available || 0);
                        return totalCount > 0 ? ((availableCount / totalCount) * 100).toFixed(1) : '0.0';
                      })()}%
                    </div>
                    <div>可用率</div>
                  </Card>
                </Col>
              </Row>
            </div>

            {/* 分类详细统计 */}
            <div>
              <Title level={4} style={{ marginBottom: 16 }}>分类详细统计</Title>
              <Row gutter={[24, 24]}>
                {/* 头像改版 */}
                <Col span={8}>
                  <Card 
                    title="头像改版" 
                    variant="borderless"
                    style={{ background: '#f6ffed' }}
                  >
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>总数：</Text>
                        <Text strong>{detailStatsData.avatarRedesign?.total || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>可用数：</Text>
                        <Text style={{ color: '#52c41a' }}>{detailStatsData.avatarRedesign?.available || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>已用数：</Text>
                        <Text style={{ color: '#faad14' }}>{detailStatsData.avatarRedesign?.used || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>使用率：</Text>
                        <Text strong style={{ color: '#722ed1' }}>{(detailStatsData.avatarRedesign?.rate || 0).toFixed(1)}%</Text>
                      </div>
                    </Space>
                  </Card>
                </Col>

                {/* 装修风格 */}
                <Col span={8}>
                  <Card 
                    title="装修风格" 
                    variant="borderless"
                    style={{ background: '#fff7e6' }}
                  >
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>总数：</Text>
                        <Text strong>{detailStatsData.roomDecoration?.total || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>可用数：</Text>
                        <Text style={{ color: '#52c41a' }}>{detailStatsData.roomDecoration?.available || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>已用数：</Text>
                        <Text style={{ color: '#faad14' }}>{detailStatsData.roomDecoration?.used || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>使用率：</Text>
                        <Text strong style={{ color: '#722ed1' }}>{(detailStatsData.roomDecoration?.rate || 0).toFixed(1)}%</Text>
                      </div>
                    </Space>
                  </Card>
                </Col>

                {/* 照片扩图 */}
                <Col span={8}>
                  <Card 
                    title="照片扩图" 
                    variant="borderless"
                    style={{ background: '#f0f5ff' }}
                  >
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>总数：</Text>
                        <Text strong>{detailStatsData.photoExtension?.total || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>可用数：</Text>
                        <Text style={{ color: '#52c41a' }}>{detailStatsData.photoExtension?.available || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>已用数：</Text>
                        <Text style={{ color: '#faad14' }}>{detailStatsData.photoExtension?.used || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>使用率：</Text>
                        <Text strong style={{ color: '#722ed1' }}>{(detailStatsData.photoExtension?.rate || 0).toFixed(1)}%</Text>
                      </div>
                    </Space>
                  </Card>
                </Col>
              </Row>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Text type="secondary">暂无数据</Text>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ResourceManagement;