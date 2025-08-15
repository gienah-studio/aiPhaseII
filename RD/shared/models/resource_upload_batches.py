from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from shared.database.session import Base
from datetime import datetime
import enum

class UploadType(enum.Enum):
    single = "single"
    batch = "batch"

class UploadStatus(enum.Enum):
    uploading = "uploading"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class ResourceUploadBatches(Base):
    """资源库上传批次表模型"""
    __tablename__ = "resource_upload_batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_code = Column(String(100), nullable=False, unique=True, comment="批次编号")
    category_id = Column(Integer, ForeignKey("resource_categories.id"), nullable=False, comment="分类ID")
    upload_type = Column(Enum(UploadType), nullable=False, comment="上传类型：single-单张，batch-批量")
    original_filename = Column(String(500), comment="原始文件名（压缩包名或图片名）")
    total_files = Column(Integer, nullable=False, default=0, comment="总文件数")
    processed_files = Column(Integer, nullable=False, default=0, comment="已处理文件数")
    failed_files = Column(Integer, nullable=False, default=0, comment="失败文件数")
    upload_status = Column(Enum(UploadStatus), nullable=False, default=UploadStatus.uploading, comment="上传状态")
    uploader_id = Column(Integer, nullable=False, comment="上传者ID")
    uploader_name = Column(String(100), nullable=False, comment="上传者姓名")
    upload_notes = Column(Text, comment="上传备注")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联关系
    category = relationship("ResourceCategories", foreign_keys=[category_id])
    images = relationship("ResourceImages", back_populates="batch")