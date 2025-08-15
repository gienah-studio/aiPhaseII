import React from 'react';
import {
  Card,
  Image,
  Tag,
  Rate,
  Space,
  Button,
  Popconfirm,
  Typography,
  Tooltip,
  Checkbox,
  Row,
  Col
} from 'antd';
import {
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  FileImageOutlined,
  TagsOutlined
} from '@ant-design/icons';
import type { ResourceItem } from './ResourceTable';
import styles from './index.module.css';

const { Text, Paragraph } = Typography;
const { Meta } = Card;

interface ResourceCardsProps {
  data: ResourceItem[];
  loading?: boolean;
  selectedRowKeys: string[];
  onSelectionChange: (selectedRowKeys: string[]) => void;
  onView: (record: ResourceItem) => void;
  onDelete: (record: ResourceItem) => void;
}

const ResourceCards: React.FC<ResourceCardsProps> = ({
  data,
  loading,
  selectedRowKeys,
  onSelectionChange,
  onView,
  onDelete
}) => {
  const getStatusConfig = (status: ResourceItem['status']) => {
    const configs = {
      available: { color: 'success', text: '可用' },
      used: { color: 'processing', text: '已使用' },
      disabled: { color: 'default', text: '已禁用' }
    };
    return configs[status];
  };

  const handleCardSelection = (id: string, checked: boolean) => {
    const newSelectedKeys = checked
      ? [...selectedRowKeys, id]
      : selectedRowKeys.filter(key => key !== id);
    onSelectionChange(newSelectedKeys);
  };

  const formatUploadTime = (timeStr: string) => {
    const date = new Date(timeStr);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className={styles.resourceCards}>
      <Row gutter={[16, 16]}>
        {data.map((item) => {
          const statusConfig = getStatusConfig(item.status);
          const isSelected = selectedRowKeys.includes(item.id);
          const isDisabled = item.status === 'disabled';

          return (
            <Col key={item.id} xs={24} sm={12} md={8} lg={6} xl={6}>
              <Card
                className={`${styles.resourceCard} ${isSelected ? styles.selectedCard : ''}`}
                loading={loading}
                cover={
                  <div className={styles.cardCover}>
                    <Image
                      src={item.thumbnail}
                      alt={item.fileName}
                      className={styles.cardImage}
                      preview={{
                        mask: <EyeOutlined />
                      }}
                      fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3Ik1RnG4W+FgYxYQQ=="
                    />
                    <div className={styles.cardOverlay}>
                      <Checkbox
                        checked={isSelected}
                        disabled={isDisabled}
                        onChange={(e) => handleCardSelection(item.id, e.target.checked)}
                        className={styles.cardCheckbox}
                      />
                      <Tag color={statusConfig.color} className={styles.statusTag}>
                        {statusConfig.text}
                      </Tag>
                    </div>
                  </div>
                }
                actions={[
                  <Tooltip title="查看详情" key="view">
                    <Button
                      type="text"
                      icon={<EyeOutlined />}
                      onClick={() => onView(item)}
                      size="small"
                    />
                  </Tooltip>,
                  <Popconfirm
                    key="delete"
                    title="确定删除这个资源吗？"
                    description="删除后无法恢复，请确认操作。"
                    onConfirm={() => onDelete(item)}
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
                ]}
              >
                <Meta
                  title={
                    <Tooltip title={item.fileName}>
                      <Text strong ellipsis className={styles.cardTitle}>
                        {item.fileName}
                      </Text>
                    </Tooltip>
                  }
                  description={
                    <div className={styles.cardDescription}>
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        {/* 分类 */}
                        <Space size="small">
                          <FileImageOutlined className={styles.infoIcon} />
                          <Tag color="blue" size="small">{item.category}</Tag>
                        </Space>

                        {/* 文件信息 */}
                        <div className={styles.fileInfo}>
                          <Text type="secondary" className={styles.infoText}>
                            {item.fileSize} • {item.dimensions}
                          </Text>
                        </div>

                        {/* 质量评分 */}
                        <div className={styles.ratingInfo}>
                          <Rate
                            value={item.qualityScore}
                            disabled
                            allowHalf
                            style={{ fontSize: 14 }}
                          />
                          <Text type="secondary" className={styles.scoreText}>
                            ({item.qualityScore}/10)
                          </Text>
                        </div>

                        {/* 标签 */}
                        {item.tags.length > 0 && (
                          <div className={styles.tagsInfo}>
                            <Space size={2} wrap>
                              <TagsOutlined className={styles.infoIcon} />
                              {item.tags.slice(0, 3).map((tag, index) => (
                                <Tag key={index} color="geekblue" size="small">
                                  {tag}
                                </Tag>
                              ))}
                              {item.tags.length > 3 && (
                                <Tooltip title={item.tags.slice(3).join(', ')}>
                                  <Tag color="default" size="small">
                                    +{item.tags.length - 3}
                                  </Tag>
                                </Tooltip>
                              )}
                            </Space>
                          </div>
                        )}

                        {/* 上传时间 */}
                        <div className={styles.timeInfo}>
                          <Space size="small">
                            <ClockCircleOutlined className={styles.infoIcon} />
                            <Text type="secondary" className={styles.timeText}>
                              {formatUploadTime(item.uploadTime)}
                            </Text>
                          </Space>
                        </div>
                      </Space>
                    </div>
                  }
                />
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
};

export default ResourceCards;