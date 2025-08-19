import React, { useState } from 'react';
import {
  Upload,
  Button,
  Card,
  Tabs,
  Form,
  Select,
  Input,
  Row,
  Col,
  Divider,
  Space,
  Progress,
  Typography,
  message,
  Modal,
  List,
  Image
} from 'antd';
import {
  CloudUploadOutlined,
  FileZipOutlined,
  InboxOutlined,
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined
} from '@ant-design/icons';
import type { UploadProps, UploadFile } from 'antd';
import styles from './index.module.css';

const { TextArea } = Input;
const { Text, Title } = Typography;
const { Dragger } = Upload;

export interface UploadFormData {
  category: string;
  description: string;
}

interface ResourceUploadProps {
  categories: Array<{ label: string; value: string }>;
  onUpload: (files: UploadFile[], formData: UploadFormData) => Promise<void>;
  onBatchUpload: (file: UploadFile, formData: UploadFormData) => Promise<void>;
}

const ResourceUpload: React.FC<ResourceUploadProps> = ({
  categories,
  onUpload,
  onBatchUpload
}) => {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [batchFileList, setBatchFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewImage, setPreviewImage] = useState('');
  const [previewTitle, setPreviewTitle] = useState('');

  const handleSingleUpload: UploadProps['customRequest'] = ({ file, onSuccess, onError }) => {
    // 模拟上传进度
    let progress = 0;
    const timer = setInterval(() => {
      progress += 10;
      setUploadProgress(progress);
      if (progress >= 100) {
        clearInterval(timer);
        onSuccess?.(file);
        setUploadProgress(0);
      }
    }, 200);
  };

  const handleBatchFileChange: UploadProps['onChange'] = ({ fileList: newFileList }) => {
    setBatchFileList(newFileList);
  };

  const handleBatchSubmit = async () => {
    try {
      const formData = await form.validateFields();
      if (batchFileList.length === 0) {
        message.warning('请先选择要上传的压缩包');
        return;
      }

      setUploading(true);
      await onBatchUpload(batchFileList[0], formData);
      message.success('批量上传成功！');
      setBatchFileList([]);
      form.resetFields();
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '批量上传失败，请重试';
      message.error(errorMsg);
    } finally {
      setUploading(false);
    }
  };

  const handlePreview = async (file: UploadFile) => {
    if (!file.url && !file.preview) {
      file.preview = await getBase64(file.originFileObj as File);
    }
    setPreviewImage(file.url || (file.preview as string));
    setPreviewVisible(true);
    setPreviewTitle(file.name || file.url!.substring(file.url!.lastIndexOf('/') + 1));
  };

  const getBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = (error) => reject(error);
    });

  const handleSubmit = async () => {
    try {
      const formData = await form.validateFields();
      if (fileList.length === 0) {
        message.warning('请先选择要上传的文件');
        return;
      }

      setUploading(true);
      await onUpload(fileList, formData);
      message.success('上传成功！');
      setFileList([]);
      form.resetFields();
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '上传失败，请重试';
      message.error(errorMsg);
    } finally {
      setUploading(false);
    }
  };

  const uploadButton = (
    <div>
      <PlusOutlined />
      <div style={{ marginTop: 8 }}>上传图片</div>
    </div>
  );

  const beforeUpload = (file: File) => {
    const isImage = file.type.startsWith('image/');
    if (!isImage) {
      message.error('只能上传图片文件！');
      return false;
    }
    const isLt10M = file.size / 1024 / 1024 < 10;
    if (!isLt10M) {
      message.error('图片文件大小不能超过 10MB！');
      return false;
    }
    return false; // 阻止自动上传
  };

  const beforeBatchUpload = (file: File) => {
    const isArchive = ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed'].includes(file.type);
    if (!isArchive) {
      message.error('只能上传压缩包文件（ZIP、RAR、7Z）！');
      return false;
    }
    const isLt100M = file.size / 1024 / 1024 < 100;
    if (!isLt100M) {
      message.error('压缩包大小不能超过 100MB！');
      return false;
    }
    return false; // 阻止自动上传，等待用户手动点击上传按钮
  };

  const handleChange: UploadProps['onChange'] = async ({ fileList: newFileList }) => {
    // 为新添加的文件生成预览URL
    const updatedFileList = await Promise.all(
      newFileList.map(async (file) => {
        if (!file.url && !file.preview && file.originFileObj) {
          try {
            file.preview = await getBase64(file.originFileObj as File);
          } catch (error) {
            console.error('生成预览失败:', error);
          }
        }
        return file;
      })
    );
    setFileList(updatedFileList);
  };

  const handleRemove = (file: UploadFile) => {
    const index = fileList.indexOf(file);
    const newFileList = fileList.slice();
    newFileList.splice(index, 1);
    setFileList(newFileList);
  };

  return (
    <div className={styles.resourceUpload}>
      <Card title="资源上传" className={styles.uploadCard}>
        <Tabs 
          defaultActiveKey="single" 
          className={styles.uploadTabs}
          items={[
            {
              key: 'single',
              label: '单个上传',
              children: (
                <div className={styles.uploadContent}>
                  <Dragger
                    name="images"
                    multiple
                    accept=".jpg,.jpeg,.png,.gif,.bmp,.webp"
                    fileList={fileList}
                    customRequest={handleSingleUpload}
                    beforeUpload={beforeUpload}
                    onChange={handleChange}
                    onPreview={handlePreview}
                    onRemove={handleRemove}
                    className={styles.uploadDragger}
                  >
                    <p className="ant-upload-drag-icon">
                      <CloudUploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                    </p>
                    <p className="ant-upload-text">点击或拖拽图片到此区域</p>
                    <p className="ant-upload-hint">
                      支持 JPG、PNG、GIF、WebP 格式，单个文件不超过 10MB
                    </p>
                  </Dragger>

                  {/* 上传进度 */}
                  {uploadProgress > 0 && uploadProgress < 100 && (
                    <div className={styles.uploadProgress}>
                      <Progress percent={uploadProgress} status="active" />
                      <Text type="secondary">正在上传...</Text>
                    </div>
                  )}

                  {/* 已选择的文件列表 */}
                  {fileList.length > 0 && (
                    <div className={styles.fileList}>
                      <Title level={5}>已选择文件 ({fileList.length})</Title>
                      <List
                        grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4, xl: 4, xxl: 6 }}
                        dataSource={fileList}
                        renderItem={(file) => (
                          <List.Item>
                            <Card
                              size="small"
                              cover={
                                <div className={styles.filePreview}>
                                  <Image
                                    src={file.url || file.thumbUrl || file.preview}
                                    alt={file.name}
                                    preview={false}
                                    onClick={() => handlePreview(file)}
                                    fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3Ik1RnG4W+FgYxN"
                                  />
                                </div>
                              }
                              actions={[
                                <EyeOutlined key="preview" onClick={() => handlePreview(file)} />,
                                <DeleteOutlined key="delete" onClick={() => handleRemove(file)} />
                              ]}
                            >
                              <Card.Meta
                                title={
                                  <Text ellipsis style={{ width: '100%' }}>
                                    {file.name}
                                  </Text>
                                }
                              />
                            </Card>
                          </List.Item>
                        )}
                      />
                    </div>
                  )}
                </div>
              )
            },
            {
              key: 'batch',
              label: '批量上传',
              children: (
                <div className={styles.uploadContent}>
                  <Dragger
                    name="batch"
                    accept=".zip,.rar,.7z"
                    fileList={batchFileList}
                    beforeUpload={beforeBatchUpload}
                    onChange={handleBatchFileChange}
                    showUploadList={true}
                    className={styles.uploadDragger}
                  >
                    <p className="ant-upload-drag-icon">
                      <FileZipOutlined style={{ fontSize: 48, color: '#52c41a' }} />
                    </p>
                    <p className="ant-upload-text">上传压缩包进行批量导入</p>
                    <p className="ant-upload-hint">
                      支持 ZIP、RAR、7Z 格式，压缩包不超过 100MB
                    </p>
                  </Dragger>
                  <div className={styles.batchTips}>
                    <Title level={5}>批量上传说明：</Title>
                    <ul>
                      <li>压缩包内的图片文件将自动解压并上传</li>
                      <li>支持嵌套文件夹，系统会自动扫描所有图片</li>
                      <li>建议压缩包内文件数量不超过 500 个</li>
                      <li>上传后会根据文件夹结构自动分类</li>
                    </ul>
                  </div>
                </div>
              )
            }
          ]}
        />

        <Divider />

        {/* 上传设置表单 */}
        <Form
          form={form}
          layout="vertical"
        >
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item
                label="选择分类"
                name="category"
                rules={[{ required: true, message: '请选择资源分类' }]}
              >
                <Select placeholder="请选择资源分类" options={categories} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label="备注信息"
                name="description"
              >
                <TextArea
                  placeholder="可选：添加上传备注或资源描述"
                  rows={3}
                  maxLength={500}
                  showCount
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>

        {/* 上传按钮 */}
        <div className={styles.uploadActions}>
          <Space>
            <Button
              type="primary"
              size="large"
              loading={uploading}
              onClick={fileList.length > 0 ? handleSubmit : handleBatchSubmit}
              disabled={fileList.length === 0 && batchFileList.length === 0}
            >
              {fileList.length > 0 
                ? `开始上传 (${fileList.length} 个文件)` 
                : batchFileList.length > 0
                ? `批量上传 (${batchFileList.length} 个压缩包)`
                : '开始上传'
              }
            </Button>
            <Button
              size="large"
              onClick={() => {
                setFileList([]);
                setBatchFileList([]);
                form.resetFields();
              }}
              disabled={uploading}
            >
              清空列表
            </Button>
          </Space>
        </div>
      </Card>

      {/* 图片预览弹窗 */}
      <Modal
        open={previewVisible}
        title={previewTitle}
        footer={null}
        onCancel={() => setPreviewVisible(false)}
        width="80%"
        centered
      >
        <img
          alt="preview"
          style={{ width: '100%' }}
          src={previewImage}
        />
      </Modal>
    </div>
  );
};

export default ResourceUpload;