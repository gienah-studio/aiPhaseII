import React, { useState } from 'react';
import {
  Card,
  Tree,
  Space,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Popconfirm,
  Typography,
  message,
  Divider,
  Badge,
  Tooltip
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FolderOutlined,
  FolderOpenOutlined,
  FileImageOutlined,
  EyeOutlined,
  FolderAddOutlined
} from '@ant-design/icons';
import type { DataNode } from 'antd/es/tree';
import styles from './index.module.css';

const { Text, Title } = Typography;
const { TextArea } = Input;

export interface CategoryNode {
  id: string;
  name: string;
  description?: string;
  parentId?: string;
  resourceCount: number;
  children?: CategoryNode[];
  icon?: string;
  color?: string;
}

interface CategoryManagerProps {
  categories: CategoryNode[];
  selectedCategory?: string;
  onCategorySelect: (categoryId: string, category?: CategoryNode) => void;
  onCategoryAdd: (category: Omit<CategoryNode, 'id' | 'resourceCount'>) => Promise<void>;
  onCategoryEdit: (categoryId: string, category: Partial<CategoryNode>) => Promise<void>;
  onCategoryDelete: (categoryId: string) => Promise<void>;
  loading?: boolean;
}

const CategoryManager: React.FC<CategoryManagerProps> = ({
  categories,
  selectedCategory,
  onCategorySelect,
  onCategoryAdd,
  onCategoryEdit,
  onCategoryDelete,
  loading
}) => {
  const [form] = Form.useForm();
  const [addModalVisible, setAddModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [currentCategory, setCurrentCategory] = useState<CategoryNode | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [actionLoading, setActionLoading] = useState(false);

  // 转换分类数据为树节点格式
  const convertToTreeData = (categories: CategoryNode[]): DataNode[] => {
    return categories.map((category) => ({
      key: category.id,
      title: (
        <div className={styles.treeNodeTitle}>
          <Space>
            {category.children && category.children.length > 0 ? (
              <FolderOutlined style={{ color: category.color || '#1890ff' }} />
            ) : (
              <FileImageOutlined style={{ color: category.color || '#8c8c8c' }} />
            )}
            <Text
              strong={category.id === selectedCategory}
              className={styles.categoryName}
            >
              {category.name || '未命名分类'}
            </Text>
          </Space>
        </div>
      ),
      children: category.children ? convertToTreeData(category.children) : undefined,
      isLeaf: !category.children || category.children.length === 0
    }));
  };

  // 查找分类节点
  const findCategoryById = (categories: CategoryNode[], id: string): CategoryNode | null => {
    for (const category of categories) {
      if (category.id === id) {
        return category;
      }
      if (category.children) {
        const found = findCategoryById(category.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  // 获取所有父级分类（用于添加子分类）
  const getParentOptions = (categories: CategoryNode[], excludeId?: string): Array<{ label: string; value: string }> => {
    const options: Array<{ label: string; value: string }> = [
      { label: '根分类', value: '' }
    ];

    const traverse = (nodes: CategoryNode[], prefix = '') => {
      nodes.forEach(node => {
        if (node.id !== excludeId) {
          options.push({
            label: `${prefix}${node.name}`,
            value: node.id
          });
          if (node.children) {
            traverse(node.children, `${prefix}${node.name} > `);
          }
        }
      });
    };

    traverse(categories);
    return options;
  };

  const handleAddCategory = () => {
    form.resetFields();
    setAddModalVisible(true);
  };

  const handleEditCategory = () => {
    if (!selectedCategory) {
      message.warning('请先选择要编辑的分类');
      return;
    }

    const category = findCategoryById(categories, selectedCategory);
    if (!category) {
      message.error('未找到选中的分类');
      return;
    }

    setCurrentCategory(category);
    form.setFieldsValue({
      name: category.name,
      description: category.description,
      parentId: category.parentId || '',
      color: category.color
    });
    setEditModalVisible(true);
  };

  const handleViewCategory = () => {
    if (!selectedCategory) {
      message.warning('请先选择要查看的分类');
      return;
    }

    const category = findCategoryById(categories, selectedCategory);
    if (!category) {
      message.error('未找到选中的分类');
      return;
    }

    setCurrentCategory(category);
    setViewModalVisible(true);
  };

  const handleDeleteCategory = async () => {
    if (!selectedCategory) {
      message.warning('请先选择要删除的分类');
      return;
    }

    const category = findCategoryById(categories, selectedCategory);
    if (!category) {
      message.error('未找到选中的分类');
      return;
    }

    if (category.resourceCount > 0) {
      message.error('该分类下还有资源，无法删除');
      return;
    }

    if (category.children && category.children.length > 0) {
      message.error('该分类下还有子分类，无法删除');
      return;
    }

    try {
      setActionLoading(true);
      await onCategoryDelete(selectedCategory);
      message.success('删除成功');
      onCategorySelect('');
    } catch (error) {
      message.error('删除失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddSubmit = async () => {
    try {
      const values = await form.validateFields();
      setActionLoading(true);
      await onCategoryAdd({
        name: values.name,
        description: values.description,
        parentId: values.parentId || undefined,
        color: values.color,
        children: []
      });
      message.success('添加成功');
      setAddModalVisible(false);
      form.resetFields();
    } catch (error) {
      message.error('添加失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleEditSubmit = async () => {
    if (!currentCategory) return;

    try {
      const values = await form.validateFields();
      setActionLoading(true);
      await onCategoryEdit(currentCategory.id, {
        name: values.name,
        description: values.description,
        parentId: values.parentId || undefined,
        color: values.color
      });
      message.success('编辑成功');
      setEditModalVisible(false);
      setCurrentCategory(null);
      form.resetFields();
    } catch (error) {
      message.error('编辑失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleTreeSelect = (selectedKeys: React.Key[]) => {
    const key = selectedKeys[0] as string;
    if (key) {
      const category = findCategoryById(categories, key);
      onCategorySelect(key, category || undefined);
    } else {
      onCategorySelect('');
    }
  };

  const colorOptions = [
    { label: '蓝色', value: '#1890ff' },
    { label: '绿色', value: '#52c41a' },
    { label: '橙色', value: '#faad14' },
    { label: '红色', value: '#ff4d4f' },
    { label: '紫色', value: '#722ed1' },
    { label: '青色', value: '#13c2c2' },
    { label: '粉色', value: '#eb2f96' },
    { label: '灰色', value: '#8c8c8c' }
  ];

  const treeData = convertToTreeData(categories);
  const selectedCategoryData = selectedCategory ? findCategoryById(categories, selectedCategory) : null;

  return (
    <div className={styles.categoryManager}>
      <Card title="分类管理" className={styles.categoryCard}>
        <div className={styles.categoryTree}>
          <Tree
            showLine={{ showLeafIcon: false }}
            showIcon
            treeData={treeData}
            selectedKeys={selectedCategory ? [selectedCategory] : []}
            expandedKeys={expandedKeys}
            onSelect={handleTreeSelect}
            onExpand={setExpandedKeys}
            loadData={undefined}
            className={styles.tree}
          />

          {treeData.length === 0 && (
            <div className={styles.emptyTree}>
              <FolderAddOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
              <Text type="secondary">暂无分类，点击下方按钮添加</Text>
            </div>
          )}
        </div>

        <Divider />

        <Space direction="vertical" style={{ width: '100%' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={handleAddCategory}
            loading={actionLoading}
          >
            新增分类
          </Button>

          <Button
            icon={<EyeOutlined />}
            block
            disabled={!selectedCategory}
            onClick={handleViewCategory}
          >
            查看详情
          </Button>

          <Button
            icon={<EditOutlined />}
            block
            disabled={!selectedCategory}
            onClick={handleEditCategory}
            loading={actionLoading}
          >
            编辑分类
          </Button>

          <Popconfirm
            title="确定删除该分类吗？"
            description="删除后无法恢复，且该分类下不能有资源或子分类。"
            onConfirm={handleDeleteCategory}
            disabled={!selectedCategory}
            okText="确定"
            cancelText="取消"
          >
            <Button
              danger
              icon={<DeleteOutlined />}
              block
              disabled={!selectedCategory}
              loading={actionLoading}
            >
              删除分类
            </Button>
          </Popconfirm>
        </Space>

      </Card>

      {/* 添加分类弹窗 */}
      <Modal
        title="新增分类"
        open={addModalVisible}
        onOk={handleAddSubmit}
        onCancel={() => {
          setAddModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={actionLoading}
        okText="确定"
        cancelText="取消"
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="分类名称"
            name="name"
            rules={[
              { required: true, message: '请输入分类名称' },
              { max: 50, message: '分类名称不能超过50个字符' }
            ]}
          >
            <Input placeholder="请输入分类名称" />
          </Form.Item>
          <Form.Item
            label="父级分类"
            name="parentId"
          >
            <Select
              placeholder="选择父级分类（不选择为根分类）"
              options={getParentOptions(categories)}
              allowClear
            />
          </Form.Item>
          <Form.Item
            label="分类颜色"
            name="color"
          >
            <Select placeholder="选择分类颜色">
              {colorOptions.map(color => (
                <Select.Option key={color.value} value={color.value}>
                  <Space>
                    <div
                      style={{
                        width: 16,
                        height: 16,
                        backgroundColor: color.value,
                        borderRadius: 2
                      }}
                    />
                    {color.label}
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="分类描述"
            name="description"
          >
            <TextArea
              placeholder="请输入分类描述"
              rows={3}
              maxLength={200}
              showCount
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑分类弹窗 */}
      <Modal
        title="编辑分类"
        open={editModalVisible}
        onOk={handleEditSubmit}
        onCancel={() => {
          setEditModalVisible(false);
          setCurrentCategory(null);
          form.resetFields();
        }}
        confirmLoading={actionLoading}
        okText="确定"
        cancelText="取消"
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="分类名称"
            name="name"
            rules={[
              { required: true, message: '请输入分类名称' },
              { max: 50, message: '分类名称不能超过50个字符' }
            ]}
          >
            <Input placeholder="请输入分类名称" />
          </Form.Item>
          <Form.Item
            label="父级分类"
            name="parentId"
          >
            <Select
              placeholder="选择父级分类（不选择为根分类）"
              options={getParentOptions(categories, currentCategory?.id)}
              allowClear
            />
          </Form.Item>
          <Form.Item
            label="分类颜色"
            name="color"
          >
            <Select placeholder="选择分类颜色">
              {colorOptions.map(color => (
                <Select.Option key={color.value} value={color.value}>
                  <Space>
                    <div
                      style={{
                        width: 16,
                        height: 16,
                        backgroundColor: color.value,
                        borderRadius: 2
                      }}
                    />
                    {color.label}
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="分类描述"
            name="description"
          >
            <TextArea
              placeholder="请输入分类描述"
              rows={3}
              maxLength={200}
              showCount
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看分类弹窗 */}
      <Modal
        title="分类详情"
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false);
          setCurrentCategory(null);
        }}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={600}
      >
        {currentCategory && (
          <div className={styles.categoryDetail}>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div className={styles.detailItem}>
                <Text strong>分类名称：</Text>
                <Text>{currentCategory.name}</Text>
              </div>
              <div className={styles.detailItem}>
                <Text strong>资源数量：</Text>
                <Badge count={currentCategory.resourceCount} showZero />
              </div>
              <div className={styles.detailItem}>
                <Text strong>分类颜色：</Text>
                <Space>
                  <div
                    style={{
                      width: 20,
                      height: 20,
                      backgroundColor: currentCategory.color || '#8c8c8c',
                      borderRadius: 4,
                      border: '1px solid #d9d9d9'
                    }}
                  />
                  <Text>{currentCategory.color || '默认'}</Text>
                </Space>
              </div>
              {currentCategory.description && (
                <div className={styles.detailItem}>
                  <Text strong>分类描述：</Text>
                  <div style={{ marginTop: 8 }}>
                    <Text>{currentCategory.description}</Text>
                  </div>
                </div>
              )}
              {currentCategory.children && currentCategory.children.length > 0 && (
                <div className={styles.detailItem}>
                  <Text strong>子分类：</Text>
                  <div style={{ marginTop: 8 }}>
                    <Space wrap>
                      {currentCategory.children.map(child => (
                        <Badge key={child.id} count={child.resourceCount} size="small">
                          <Button size="small" type="ghost">
                            {child.name}
                          </Button>
                        </Badge>
                      ))}
                    </Space>
                  </div>
                </div>
              )}
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default CategoryManager;
