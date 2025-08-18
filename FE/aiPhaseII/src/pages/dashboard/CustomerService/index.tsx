import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Select,
  Modal,
  Form,
  message,
  Popconfirm,
  Tag,
  Typography,
  Upload,
  Divider,
  ConfigProvider
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  UploadOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import {
  getVirtualCustomerServices,
  createVirtualCustomerService,
  updateVirtualCustomerService,
  deleteVirtualCustomerService,
  importCustomerService,
  type VirtualCustomerServiceInfo,
  type VirtualCustomerServiceParams,
  type VirtualCustomerServiceCreate,
  type VirtualCustomerServiceUpdate
} from '../../../api';
import styles from './index.module.css';

const { Title } = Typography;
const { Option } = Select;

const CustomerService: React.FC = () => {
  // 数据状态
  const [data, setData] = useState<VirtualCustomerServiceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // 搜索状态 - 注意：根据接口文档，API只支持分页参数，本地搜索功能保留
  const [searchParams, setSearchParams] = useState<{
    name?: string;
    account?: string;
    level?: string;
    status?: string;
  }>({});

  // 弹窗状态
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<VirtualCustomerServiceInfo | null>(null);
  const [form] = Form.useForm();

  // 导入状态
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [uploading, setUploading] = useState(false);

  // 获取数据
  const fetchData = async (params?: { page?: number; size?: number }) => {
    try {
      setLoading(true);
      // 根据接口文档，只传递分页参数给API
      const queryParams: VirtualCustomerServiceParams = {
        page: params?.page || pagination.current,
        size: params?.size || pagination.pageSize
      };

      const response = await getVirtualCustomerServices(queryParams);

      // 验证响应数据结构
      if (!response || !Array.isArray(response.items)) {
        console.error('客服列表数据格式异常:', response);
        message.error('客服列表数据格式异常');
        setData([]);
        setPagination(prev => ({
          ...prev,
          total: 0,
          current: params?.page || pagination.current,
          pageSize: params?.size || pagination.pageSize
        }));
        return;
      }

      // 应用本地搜索过滤（因为API不支持搜索参数）
      let filteredData = response.items;
      if (searchParams.name) {
        filteredData = filteredData.filter(item =>
          item.name && item.name.toLowerCase().includes(searchParams.name!.toLowerCase())
        );
      }
      if (searchParams.account) {
        filteredData = filteredData.filter(item =>
          item.account && item.account.toLowerCase().includes(searchParams.account!.toLowerCase())
        );
      }
      if (searchParams.level) {
        filteredData = filteredData.filter(item => item.level === searchParams.level);
      }

      setData(filteredData);
      setPagination(prev => ({
        ...prev,
        total: response.total || 0,
        current: response.page || params?.page || pagination.current,
        pageSize: response.size || params?.size || pagination.pageSize
      }));
    } catch (error) {
      message.error('获取客服列表失败');
      console.error('获取客服列表失败:', error);
      // 设置空数据以避免界面错误
      setData([]);
      setPagination(prev => ({
        ...prev,
        total: 0,
        current: params?.page || pagination.current,
        pageSize: params?.size || pagination.pageSize
      }));
    } finally {
      setLoading(false);
    }
  };

  // 初始化数据
  useEffect(() => {
    fetchData();
  }, []);

  // 搜索处理
  const handleSearch = () => {
    setPagination(prev => ({ ...prev, current: 1 }));
    fetchData({ page: 1 });
  };

  // 重置搜索
  const handleReset = () => {
    setSearchParams({});
    setPagination(prev => ({ ...prev, current: 1 }));
    fetchData({ page: 1 });
  };

  // 分页处理
  const handleTableChange = (page: number, pageSize: number) => {
    setPagination(prev => ({ ...prev, current: page, pageSize }));
    fetchData({ page, size: pageSize });
  };

  // 打开创建/编辑弹窗
  const handleOpenModal = (record?: VirtualCustomerServiceInfo) => {
    setEditingRecord(record || null);
    setModalVisible(true);

    if (record) {
      form.setFieldsValue({
        name: record.name,
        account: record.account
      });
    } else {
      form.resetFields();
    }
  };

  // 关闭弹窗
  const handleCloseModal = () => {
    setModalVisible(false);
    setEditingRecord(null);
    form.resetFields();
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingRecord) {
        // 更新
        const updateData: VirtualCustomerServiceUpdate = {
          name: values.name
        };
        await updateVirtualCustomerService(editingRecord.id, updateData);
        message.success('更新客服信息成功');
      } else {
        // 创建
        const createData: VirtualCustomerServiceCreate = {
          name: values.name,
          account: values.account,
          initialPassword: values.initialPassword || '123456'
        };
        await createVirtualCustomerService(createData);
        message.success('创建客服成功');
      }

      handleCloseModal();
      fetchData();
    } catch (error) {
      message.error(editingRecord ? '更新客服信息失败' : '创建客服失败');
      console.error('操作失败:', error);
    }
  };

  // 删除客服
  const handleDelete = async (record: VirtualCustomerServiceInfo) => {
    try {
      await deleteVirtualCustomerService(record.id);
      message.success('删除客服成功');
      fetchData();
    } catch (error) {
      message.error('删除客服失败');
      console.error('删除客服失败:', error);
    }
  };

  // 处理文件导入
  const handleImport = async (file: File) => {
    try {
      setUploading(true);
      const result = await importCustomerService(file);
      message.success(`导入成功！成功导入 ${result.totalImported} 条记录${result.failedCount > 0 ? `，失败 ${result.failedCount} 条` : ''}`);

      if (result.failedCount > 0 && result.failedDetails.length > 0) {
        Modal.warning({
          title: '部分导入失败',
          content: (
            <div>
              <p>失败详情：</p>
              <ul>
                {result.failedDetails.map((detail, index) => (
                  <li key={`failed-detail-${index}-${detail.substring(0, 10)}`}>{detail}</li>
                ))}
              </ul>
            </div>
          ),
          width: 600,
        });
      }

      setImportModalVisible(false);
      fetchData();
    } catch (error) {
      message.error('导入失败');
      console.error('导入失败:', error);
    } finally {
      setUploading(false);
    }
  };

  // 下载模板
  const handleDownloadTemplate = () => {
    // 创建一个简单的CSV模板
    const csvContent = 'name,account\n客服姓名,客服账号';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', '客服导入模板.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
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
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 120,
    },
    {
      title: '账号',
      dataIndex: 'account',
      key: 'account',
      width: 150,
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_time',
      key: 'last_login_time',
      width: 180,
      render: (time: string) => time ? new Date(time).toLocaleString() : '从未登录',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: VirtualCustomerServiceInfo) => (
        <Space size="small">
          <Button
            key="edit"
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          >
            编辑
          </Button>
          <Popconfirm
            key="delete"
            title="确定要删除这个客服吗？"
            onConfirm={() => handleDelete(record)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className={styles.container}>
      <Card>
        <div className={styles.header}>
          <Title level={4}>专属客服列表</Title>

          {/* 搜索区域 */}
          <div className={styles.searchArea}>
            <Space wrap>
              <Input
                key="search-name"
                placeholder="搜索姓名"
                value={searchParams.name}
                onChange={(e) => setSearchParams(prev => ({ ...prev, name: e.target.value }))}
                style={{ width: 150 }}
              />
              <Input
                key="search-account"
                placeholder="搜索账号"
                value={searchParams.account}
                onChange={(e) => setSearchParams(prev => ({ ...prev, account: e.target.value }))}
                style={{ width: 150 }}
              />
              <Button key="search-btn" type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                搜索
              </Button>
              <Button key="reset-btn" icon={<ReloadOutlined />} onClick={handleReset}>
                重置
              </Button>
            </Space>
          </div>

          <Divider />

          {/* 操作区域 */}
          <div className={styles.actionArea}>
            <Space wrap>
              <Button key="add-btn" type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
                新增客服
              </Button>
              {/*<Button key="import-btn" icon={<UploadOutlined />} onClick={() => setImportModalVisible(true)}>*/}
              {/*  批量导入*/}
              {/*</Button>*/}
              {/*<Button key="download-btn" icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>*/}
              {/*  下载模板*/}
              {/*</Button>*/}
            </Space>
          </div>
        </div>

        {/* 表格 */}
        <Table
          columns={columns}
          dataSource={data}
          rowKey={(record) => record.id || record.account || Math.random().toString()}
          loading={loading}
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
            showLessItems: true,
            onChange: handleTableChange,
            onShowSizeChange: handleTableChange,
          }}
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* 创建/编辑弹窗 */}
      <Modal
        title={editingRecord ? '编辑客服' : '新增客服'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={handleCloseModal}
        width={600}
        destroyOnHidden
        okText="确定"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            initialPassword: '123456'
          }}
        >
          <Form.Item
            name="name"
            label="姓名"
            rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input placeholder="请输入客服姓名" />
          </Form.Item>

          <Form.Item
            name="account"
            label="账号"
            rules={[{ required: true, message: '请输入账号' }]}
          >
            <Input
              placeholder="请输入客服账号"
              disabled={!!editingRecord}
            />
          </Form.Item>

          {!editingRecord && (
            <Form.Item
              name="initialPassword"
              label="初始密码"
              rules={[{ required: true, message: '请输入初始密码' }]}
            >
              <Input.Password placeholder="请输入初始密码" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* 导入弹窗 */}
      <Modal
        title="批量导入客服"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
        width={600}
      >
        <div style={{ padding: '20px 0' }}>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Typography.Title level={5}>导入说明：</Typography.Title>
              <ul>
                <li>支持 Excel (.xlsx) 和 CSV (.csv) 格式文件</li>
                <li>文件大小不超过 10MB</li>
                <li>请确保数据格式正确，必填字段：姓名、账号</li>
                <li>等级范围：1-6，默认为6</li>
              </ul>
            </div>

            <Upload.Dragger
              name="file"
              multiple={false}
              accept=".xlsx,.xls,.csv"
              beforeUpload={(file) => {
                const isValidType = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                                   file.type === 'application/vnd.ms-excel' ||
                                   file.type === 'text/csv';
                if (!isValidType) {
                  message.error('只能上传 Excel 或 CSV 文件！');
                  return false;
                }
                const isLt10M = file.size / 1024 / 1024 < 10;
                if (!isLt10M) {
                  message.error('文件大小不能超过 10MB！');
                  return false;
                }

                handleImport(file);
                return false; // 阻止自动上传
              }}
              disabled={uploading}
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
              </p>
              <p className="ant-upload-text">
                {uploading ? '正在导入...' : '点击或拖拽文件到此区域上传'}
              </p>
              <p className="ant-upload-hint">
                支持 Excel (.xlsx) 和 CSV (.csv) 格式
              </p>
            </Upload.Dragger>
          </Space>
        </div>
      </Modal>
    </div>
  );
};

export default CustomerService;
