from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean, BigInteger, JSON, DECIMAL, Enum
from sqlalchemy.orm import relationship
from shared.database.session import Base
from datetime import datetime
import enum

class UsageStatus(enum.Enum):
    available = "available"
    used = "used" 
    disabled = "disabled"

class ResourceImages(Base):
    """资源库图片表模型"""
    __tablename__ = "resource_images"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("resource_upload_batches.id"), nullable=False, comment="上传批次ID")
    category_id = Column(Integer, ForeignKey("resource_categories.id"), nullable=False, comment="分类ID")
    image_code = Column(String(100), nullable=False, unique=True, comment="图片编号")
    original_filename = Column(String(500), nullable=False, comment="原始文件名")
    stored_filename = Column(String(500), nullable=False, comment="存储文件名")
    file_path = Column(String(1000), nullable=False, comment="文件存储路径")
    file_url = Column(String(1000), nullable=False, comment="文件访问URL")
    file_size = Column(BigInteger, nullable=False, comment="文件大小(字节)")
    image_width = Column(Integer, comment="图片宽度")
    image_height = Column(Integer, comment="图片高度")
    file_format = Column(String(20), nullable=False, comment="文件格式(jpg,png,etc)")
    file_hash = Column(String(64), comment="MD5哈希值，用于去重")
    usage_status = Column(Enum(UsageStatus), nullable=False, default=UsageStatus.available, comment="使用状态")
    used_at = Column(DateTime, comment="使用时间")
    used_in_task_id = Column(Integer, ForeignKey("tasks.id"), comment="使用的任务ID")
    quality_score = Column(DECIMAL(3,2), comment="图片质量评分(0-10)")
    tags = Column(JSON, comment="图片标签(JSON数组)")
    upload_notes = Column(Text, comment="上传备注")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否删除")
    deleted_at = Column(DateTime, comment="删除时间")
    deleted_reason = Column(String(500), comment="删除原因")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联关系
    batch = relationship("ResourceUploadBatches", back_populates="images")
    category = relationship("ResourceCategories", foreign_keys=[category_id])
    task = relationship("Tasks", foreign_keys=[used_in_task_id])