import os
import uuid
from datetime import datetime, timedelta
from typing import Union, List, Dict, Any, Optional
import oss2
from oss2.exceptions import OssError
import logging

logger = logging.getLogger(__name__)

class OSSClient:
    """阿里云OSS文件上传客户端"""
    
    def __init__(self):
        """初始化OSS客户端"""
        try:
            # 从环境变量获取配置
            self.access_key_id = os.getenv('ACCESSKEYID')
            self.access_key_secret = os.getenv('ACCESSKEYSECRET')
            self.bucket_name = os.getenv('OSS_BUCKET_NAME')
            self.endpoint = os.getenv('OSS_ENDPOINT')
            self.base_url = os.getenv('OSS_BASE_URL')
            
            if not all([self.access_key_id, self.access_key_secret, self.bucket_name, self.endpoint]):
                raise ValueError("OSS配置不完整，请检查环境变量")
            
            # 创建认证和桶对象
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            
            logger.info(f"OSS客户端初始化成功，Bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"OSS客户端初始化失败: {str(e)}")
            raise
    
    def generate_object_key(self, category_code: str, original_filename: str) -> str:
        """
        生成OSS对象键（文件路径）
        
        Args:
            category_code: 分类代码
            original_filename: 原始文件名
            
        Returns:
            str: 生成的对象键
        """
        # 获取文件扩展名
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}{file_ext}"
        
        # 构建路径: resources/{category_code}/{year}/{month}/{filename}
        now = datetime.now()
        object_key = f"resources/{category_code}/{now.year}/{now.month:02d}/{filename}"
        
        return object_key
    
    def upload_file(self, file_content: bytes, object_key: str, 
                   content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        上传单个文件到OSS
        
        Args:
            file_content: 文件内容
            object_key: OSS对象键
            content_type: 文件MIME类型
            
        Returns:
            Dict: 上传结果
        """
        try:
            # 设置上传参数
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type
            
            # 上传文件
            result = self.bucket.put_object(object_key, file_content, headers=headers)
            
            # 生成文件URL
            file_url = f"{self.base_url}/{object_key}"
            
            return {
                'success': True,
                'object_key': object_key,
                'file_url': file_url,
                'etag': result.etag,
                'request_id': result.request_id,
                'file_size': len(file_content)
            }
            
        except OssError as e:
            logger.error(f"OSS上传失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': e.code if hasattr(e, 'code') else 'UPLOAD_ERROR'
            }
        except Exception as e:
            logger.error(f"文件上传异常: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'UNKNOWN_ERROR'
            }
    
    def upload_multiple_files(self, files_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量上传文件
        
        Args:
            files_data: 文件数据列表，每个元素包含：
                - file_content: 文件内容
                - object_key: 对象键
                - content_type: MIME类型（可选）
                
        Returns:
            List[Dict]: 上传结果列表
        """
        results = []
        
        for file_data in files_data:
            result = self.upload_file(
                file_content=file_data['file_content'],
                object_key=file_data['object_key'],
                content_type=file_data.get('content_type')
            )
            
            # 添加原始文件信息
            result.update({
                'original_filename': file_data.get('original_filename'),
                'category_code': file_data.get('category_code')
            })
            
            results.append(result)
        
        return results
    
    def delete_file(self, object_key: str) -> bool:
        """
        删除OSS文件
        
        Args:
            object_key: OSS对象键
            
        Returns:
            bool: 删除是否成功
        """
        try:
            self.bucket.delete_object(object_key)
            logger.info(f"文件删除成功: {object_key}")
            return True
            
        except OssError as e:
            logger.error(f"OSS文件删除失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"文件删除异常: {str(e)}")
            return False
    
    def delete_multiple_files(self, object_keys: List[str]) -> Dict[str, Any]:
        """
        批量删除文件
        
        Args:
            object_keys: 对象键列表
            
        Returns:
            Dict: 删除结果统计
        """
        success_count = 0
        failed_keys = []
        
        # OSS批量删除API限制每次最多1000个对象
        batch_size = 1000
        
        try:
            for i in range(0, len(object_keys), batch_size):
                batch_keys = object_keys[i:i + batch_size]
                
                try:
                    # 批量删除
                    result = self.bucket.batch_delete_objects(batch_keys)
                    success_count += len(batch_keys) - len(result.delete_failed)
                    
                    # 记录失败的键
                    for failed in result.delete_failed:
                        failed_keys.append({
                            'key': failed.key,
                            'code': failed.code,
                            'message': failed.message
                        })
                        
                except Exception as e:
                    logger.error(f"批量删除失败: {str(e)}")
                    failed_keys.extend([{'key': key, 'error': str(e)} for key in batch_keys])
        
        except Exception as e:
            logger.error(f"批量删除异常: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        
        return {
            'success': True,
            'total_count': len(object_keys),
            'success_count': success_count,
            'failed_count': len(failed_keys),
            'failed_details': failed_keys if failed_keys else None
        }
    
    def generate_presigned_url(self, object_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        生成预签名URL
        
        Args:
            object_key: OSS对象键
            expires_in: 有效期（秒），默认1小时
            
        Returns:
            Optional[str]: 预签名URL
        """
        try:
            url = self.bucket.sign_url('GET', object_key, expires_in)
            return url
            
        except Exception as e:
            logger.error(f"生成预签名URL失败: {str(e)}")
            return None
    
    def get_file_info(self, object_key: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            object_key: OSS对象键
            
        Returns:
            Optional[Dict]: 文件信息
        """
        try:
            # 获取文件元数据
            result = self.bucket.head_object(object_key)
            
            return {
                'object_key': object_key,
                'file_size': result.content_length,
                'content_type': result.content_type,
                'etag': result.etag,
                'last_modified': result.last_modified,
                'metadata': result.metadata
            }
            
        except OssError as e:
            if e.status == 404:
                logger.warning(f"文件不存在: {object_key}")
            else:
                logger.error(f"获取文件信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取文件信息异常: {str(e)}")
            return None
    
    def check_file_exists(self, object_key: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            object_key: OSS对象键
            
        Returns:
            bool: 文件是否存在
        """
        try:
            self.bucket.head_object(object_key)
            return True
        except OssError as e:
            if e.status == 404:
                return False
            else:
                logger.error(f"检查文件存在性失败: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"检查文件存在性异常: {str(e)}")
            return False

# 创建全局OSS客户端实例
try:
    oss_client = OSSClient()
except Exception as e:
    logger.error(f"创建OSS客户端实例失败: {str(e)}")
    oss_client = None