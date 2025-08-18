import uuid
import logging
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from fastapi import UploadFile

from shared.models.resource_categories import ResourceCategories
from shared.models.resource_upload_batches import ResourceUploadBatches, UploadType, UploadStatus
from shared.models.resource_images import ResourceImages, UsageStatus
from shared.exceptions import BusinessException
from .oss_client import oss_client
from .image_processor import ImageProcessor
from ..schemas.resource_schemas import (
    CategoryResponse, ImageResponse, ImageListResponse, UploadResponse, 
    ResourceStatsResponse, AvailableImageResponse, UploadResult
)

logger = logging.getLogger(__name__)

class ResourceService:
    """资源库核心业务服务"""

    def __init__(self, db: Session):
        self.db = db
        self.image_processor = ImageProcessor()

    @staticmethod
    def _decode_filename(filename: str) -> str:
        """
        解码文件名，处理各种编码问题的中文字符

        Args:
            filename: 原始文件名（可能包含编码问题）

        Returns:
            str: 解码后的文件名
        """
        if not filename:
            return filename

        try:
            # 方法1: 尝试URL解码
            url_decoded = urllib.parse.unquote(filename, encoding='utf-8')
            if url_decoded != filename:
                logger.debug(f"URL解码成功: {filename} -> {url_decoded}")
                return url_decoded

            # 方法2: 智能乱码修复 - 尝试恢复中文房间类型关键词
            # 定义已知的乱码映射（基于实际观察到的乱码模式）
            garbled_mappings = {
                # 厨房相关的乱码映射（已确认）
                'σÄ¿µê┐': '厨房',  # 基于日志中观察到的实际乱码
                # 客厅相关的乱码映射（新发现）
                'σ«óσÄà': '客厅',  # 基于新日志中观察到的客厅乱码
            }

            # 检查文件名（去掉扩展名）是否在乱码映射中
            from pathlib import Path
            file_path = Path(filename)
            filename_without_ext = file_path.stem
            file_ext = file_path.suffix

            if filename_without_ext in garbled_mappings:
                corrected_filename = garbled_mappings[filename_without_ext] + file_ext
                logger.info(f"乱码文件名修复成功: {filename} -> {corrected_filename}")
                return corrected_filename

            # 方法3: 模式匹配修复 - 处理乱码 + 数字的模式
            import re

            # 定义房间类型的乱码模式映射
            room_garbled_patterns = {
                r'^σÄ¿µê┐(\d*)$': '厨房',  # 厨房的乱码模式
                r'^σ«óσÄà(\d*)$': '客厅',  # 客厅的乱码模式
            }

            for pattern, room_type in room_garbled_patterns.items():
                match = re.match(pattern, filename_without_ext)
                if match:
                    number = match.group(1) if match.group(1) else ''
                    corrected_filename = f"{room_type}{number}{file_ext}"
                    logger.info(f"模式匹配修复成功: {filename} -> {corrected_filename}")
                    return corrected_filename

            # 方法4: 尝试处理字符编码问题（UTF-8被错误解释为Latin-1的情况）
            if any(ord(char) > 127 for char in filename):
                try:
                    # 尝试将错误的Latin-1编码转回UTF-8
                    latin1_bytes = filename.encode('latin-1')
                    utf8_decoded = latin1_bytes.decode('utf-8')
                    logger.debug(f"字符编码修复成功: {filename} -> {utf8_decoded}")
                    return utf8_decoded
                except (UnicodeDecodeError, UnicodeEncodeError):
                    pass

            # 方法5: 如果包含明显的乱码字符但无法修复，生成包含房间类型的安全文件名
            garbled_chars = {'σ', 'Ä', '¿', 'µ', 'ê', '┐', 'Ã', '€', '™', '‚', 'ƒ', '„', '…', '†', '‡', 'ˆ', '‰', 'Š', '‹', 'Œ', 'Ž', ''', ''', '"', '"', '•', '–', '—', '˜', '™', 'š', '›', 'œ', 'ž', 'Ÿ'}

            if any(char in garbled_chars for char in filename):
                # 尝试从乱码中推断房间类型
                import time
                timestamp = int(time.time() * 1000)  # 毫秒级时间戳

                # 如果包含已知的房间类型乱码模式，生成对应房间类型的文件名
                if 'σÄ¿µê┐' in filename:
                    safe_filename = f"厨房_{timestamp}{file_ext}"
                elif 'σ«óσÄà' in filename:
                    safe_filename = f"客厅_{timestamp}{file_ext}"
                else:
                    safe_filename = f"房间_{timestamp}{file_ext}"

                logger.warning(f"检测到无法修复的乱码文件名，生成包含房间类型的安全文件名: {filename} -> {safe_filename}")
                return safe_filename

            logger.debug(f"文件名无需解码: {filename}")
            return filename

        except Exception as e:
            logger.warning(f"文件名解码过程中发生异常，使用原始文件名: {filename}, 错误: {str(e)}")
            return filename
    
    def get_categories(self) -> List[CategoryResponse]:
        """
        获取所有启用的分类列表
        
        Returns:
            List[CategoryResponse]: 分类列表
        """
        try:
            categories = self.db.query(ResourceCategories).filter(
                ResourceCategories.is_active == True
            ).order_by(ResourceCategories.sort_order, ResourceCategories.id).all()
            
            return [CategoryResponse.from_orm(category) for category in categories]
            
        except Exception as e:
            logger.error(f"获取分类列表失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"获取分类列表失败: {str(e)}",
                data=None
            )
    
    def upload_resources(self, category_id: int, files: List[UploadFile], 
                        uploader_id: int, uploader_name: str, 
                        upload_notes: Optional[str] = None) -> UploadResponse:
        """
        统一上传接口（支持单张图片和压缩包）
        
        Args:
            category_id: 分类ID
            files: 上传的文件列表
            uploader_id: 上传者ID
            uploader_name: 上传者姓名
            upload_notes: 上传备注
            
        Returns:
            UploadResponse: 上传结果
        """
        try:
            # 验证分类是否存在
            category = self.db.query(ResourceCategories).filter(
                ResourceCategories.id == category_id,
                ResourceCategories.is_active == True
            ).first()
            
            if not category:
                raise BusinessException(
                    code=404,
                    message="指定的分类不存在或已禁用",
                    data=None
                )
            
            # 创建上传批次
            batch_code = self._generate_batch_code()
            upload_type = UploadType.batch if len(files) > 1 else UploadType.single
            
            batch = ResourceUploadBatches(
                batch_code=batch_code,
                category_id=category_id,
                upload_type=upload_type,
                original_filename=self._decode_filename(files[0].filename) if len(files) == 1 else f"{len(files)}个文件",
                total_files=0,  # 稍后更新
                uploader_id=uploader_id,
                uploader_name=uploader_name,
                upload_notes=upload_notes,
                upload_status=UploadStatus.processing
            )
            
            self.db.add(batch)
            self.db.flush()  # 获取批次ID
            
            # 处理所有文件
            all_results = []
            total_files = 0
            
            for file in files:
                file_content = file.file.read()
                file.file.seek(0)  # 重置文件指针
                
                # 解码文件名
                decoded_filename = self._decode_filename(file.filename)

                if self.image_processor.is_zip_file(file_content):
                    # 处理ZIP文件
                    zip_results = self._process_zip_file(
                        batch.id, category.category_code, decoded_filename, file_content
                    )
                    all_results.extend(zip_results)
                    total_files += len(zip_results)
                else:
                    # 处理单张图片
                    single_result = self._process_single_image(
                        batch.id, category.category_code, decoded_filename, file_content
                    )
                    all_results.append(single_result)
                    total_files += 1
            
            # 统计结果
            success_count = sum(1 for r in all_results if r.success and not r.is_duplicate and not r.is_recovered)
            duplicate_count = sum(1 for r in all_results if r.is_duplicate)
            recovered_count = sum(1 for r in all_results if r.is_recovered)
            failed_count = sum(1 for r in all_results if not r.success)
            
            # 更新批次状态
            batch.total_files = total_files
            batch.processed_files = success_count + recovered_count
            batch.failed_files = failed_count
            batch.upload_status = UploadStatus.completed if failed_count == 0 else UploadStatus.failed
            
            self.db.commit()
            
            # 生成详细的消息反馈
            message_parts = []
            if total_files > 0:
                message_parts.append(f"总计{total_files}张")
            if duplicate_count > 0:
                message_parts.append(f"重复{duplicate_count}张")
            if recovered_count > 0:
                message_parts.append(f"恢复{recovered_count}张")
            if success_count > 0:
                message_parts.append(f"上传成功{success_count}张")
            if failed_count > 0:
                message_parts.append(f"失败{failed_count}张")
            
            success_message = "，".join(message_parts) if message_parts else "处理完成"
            
            return UploadResponse(
                success=success_count + recovered_count > 0,
                batch_id=batch.id,
                batch_code=batch_code,
                total_files=total_files,
                success_files=success_count + recovered_count,
                failed_files=failed_count,
                upload_results=all_results,
                error_message=success_message if success_count + recovered_count > 0 else "所有文件上传失败"
            )
            
        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"上传资源失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"上传资源失败: {str(e)}",
                data=None
            )
    
    def _process_zip_file(self, batch_id: int, category_code: str, 
                         zip_filename: str, zip_content: bytes) -> List[UploadResult]:
        """
        处理ZIP文件
        
        Args:
            batch_id: 批次ID
            category_code: 分类代码
            zip_filename: ZIP文件名
            zip_content: ZIP文件内容
            
        Returns:
            List[UploadResult]: 处理结果列表
        """
        results = []
        
        try:
            # 解压ZIP文件
            extracted_files = self.image_processor.extract_zip_files(zip_content)
            
            for file_info in extracted_files:
                # 解码ZIP文件中的文件名
                decoded_filename = self._decode_filename(file_info['filename'])
                result = self._process_single_image(
                    batch_id, category_code, decoded_filename, file_info['content']
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"处理ZIP文件失败: {str(e)}")
            results.append(UploadResult(
                success=False,
                filename=zip_filename,
                error=str(e)
            ))
        
        return results
    
    def _process_single_image(self, batch_id: int, category_code: str, 
                             filename: str, file_content: bytes) -> UploadResult:
        """
        处理单张图片
        
        Args:
            batch_id: 批次ID
            category_code: 分类代码
            filename: 文件名
            file_content: 文件内容
            
        Returns:
            UploadResult: 处理结果
        """
        try:
            # 验证图片格式
            if not self.image_processor.validate_image_format(file_content):
                return UploadResult(
                    success=False,
                    filename=filename,
                    error="不支持的图片格式或图片已损坏"
                )
            
            # 计算文件哈希
            file_hash = self.image_processor.calculate_file_hash(file_content)
            
            # 检查是否重复（同分类下，包括已删除的记录）
            batch = self.db.query(ResourceUploadBatches).filter(
                ResourceUploadBatches.id == batch_id
            ).first()
            
            # 先检查未删除的记录
            existing_image = self.db.query(ResourceImages).filter(
                ResourceImages.file_hash == file_hash,
                ResourceImages.category_id == batch.category_id,
                ResourceImages.is_deleted == False
            ).first()
            
            if existing_image:
                # 如果文件已存在且未删除，返回现有文件信息
                return UploadResult(
                    success=True,
                    filename=filename,
                    image_id=existing_image.id,
                    file_url=existing_image.file_url,
                    file_size=existing_image.file_size,
                    error="文件已存在，跳过上传",
                    is_duplicate=True
                )
            
            # 检查已删除的记录
            deleted_image = self.db.query(ResourceImages).filter(
                ResourceImages.file_hash == file_hash,
                ResourceImages.category_id == batch.category_id,
                ResourceImages.is_deleted == True
            ).first()
            
            if deleted_image:
                # 如果是已删除且已使用的图片，不允许恢复
                if deleted_image.usage_status == UsageStatus.used:
                    return UploadResult(
                        success=True,
                        filename=filename,
                        image_id=deleted_image.id,
                        file_url=deleted_image.file_url,
                        file_size=deleted_image.file_size,
                        error="文件曾经存在且已被使用，跳过上传",
                        is_duplicate=True
                    )
                else:
                    # 如果是已删除但未使用的图片，可以恢复
                    deleted_image.is_deleted = False
                    deleted_image.deleted_at = None
                    deleted_image.deleted_reason = None
                    deleted_image.updated_at = datetime.now()
                    
                    self.db.commit()
                    
                    return UploadResult(
                        success=True,
                        filename=filename,
                        image_id=deleted_image.id,
                        file_url=deleted_image.file_url,
                        file_size=deleted_image.file_size,
                        error="恢复已删除的文件",
                        is_recovered=True
                    )
            
            # 获取图片信息
            image_info = self.image_processor.get_image_info(file_content)
            
            # 如果需要，压缩图片
            processed_content = self.image_processor.resize_if_needed(file_content)
            
            # 生成OSS对象键
            object_key = oss_client.generate_object_key(category_code, filename)
            content_type = self.image_processor.get_content_type(filename)
            
            # 上传到OSS
            oss_result = oss_client.upload_file(
                file_content=processed_content,
                object_key=object_key,
                content_type=content_type
            )
            
            if not oss_result['success']:
                return UploadResult(
                    success=False,
                    filename=filename,
                    error=f"OSS上传失败: {oss_result.get('error', '未知错误')}"
                )
            
            # 保存到数据库
            image_code = self._generate_image_code()
            
            image = ResourceImages(
                batch_id=batch_id,
                category_id=batch.category_id,
                image_code=image_code,
                original_filename=filename,
                stored_filename=object_key.split('/')[-1],
                file_path=object_key,
                file_url=oss_result['file_url'],
                file_size=len(processed_content),
                image_width=image_info.get('width'),
                image_height=image_info.get('height'),
                file_format=image_info.get('format', '').lower(),
                file_hash=file_hash,
                usage_status=UsageStatus.available,
                quality_score=image_info.get('quality_score'),
                tags=image_info.get('tags'),
                upload_notes=None
            )
            
            try:
                self.db.add(image)
                self.db.flush()  # 获取图片ID
            except Exception as db_error:
                # 如果发生唯一约束冲突，再次检查是否有重复记录
                if "Duplicate entry" in str(db_error) and "uk_file_hash_category" in str(db_error):
                    self.db.rollback()
                    existing_image = self.db.query(ResourceImages).filter(
                        ResourceImages.file_hash == file_hash,
                        ResourceImages.category_id == batch.category_id,
                        ResourceImages.is_deleted == False
                    ).first()
                    
                    if existing_image:
                        # 删除已上传的OSS文件，因为这是重复的
                        try:
                            oss_client.delete_file(object_key)
                        except:
                            pass  # 忽略OSS删除失败
                        
                        return UploadResult(
                            success=True,
                            filename=filename,
                            image_id=existing_image.id,
                            file_url=existing_image.file_url,
                            file_size=existing_image.file_size,
                            error="文件已存在，跳过上传",
                            is_duplicate=True
                        )
                
                # 如果不是唯一约束冲突，重新抛出异常
                raise db_error
            
            return UploadResult(
                success=True,
                filename=filename,
                image_id=image.id,
                file_url=oss_result['file_url'],
                file_size=len(processed_content)
            )
            
        except Exception as e:
            logger.error(f"处理图片 {filename} 失败: {str(e)}")
            return UploadResult(
                success=False,
                filename=filename,
                error=str(e)
            )
    
    def get_resource_images(self, page: int = 1, size: int = 20, 
                           category_id: Optional[int] = None,
                           status: Optional[str] = None,
                           search_keyword: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> ImageListResponse:
        """
        获取资源图片列表
        
        Args:
            page: 页码
            size: 每页数量
            category_id: 分类ID筛选
            status: 状态筛选
            search_keyword: 搜索关键词
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            ImageListResponse: 图片列表响应
        """
        try:
            # 构建查询
            query = self.db.query(ResourceImages).filter(
                ResourceImages.is_deleted == False
            )
            
            # 添加筛选条件
            if category_id is not None:
                query = query.filter(ResourceImages.category_id == category_id)
            
            if status:
                query = query.filter(ResourceImages.usage_status == status)
            
            if search_keyword:
                query = query.filter(
                    or_(
                        ResourceImages.original_filename.contains(search_keyword),
                        ResourceImages.image_code.contains(search_keyword)
                    )
                )
            
            if start_date:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(ResourceImages.created_at >= start_datetime)
            
            if end_date:
                end_datetime = datetime.strptime(f"{end_date} 23:59:59", '%Y-%m-%d %H:%M:%S')
                query = query.filter(ResourceImages.created_at <= end_datetime)
            
            # 统计总数
            total = query.count()
            
            # 分页查询
            offset = (page - 1) * size
            images = query.order_by(desc(ResourceImages.created_at)).offset(offset).limit(size).all()
            
            # 获取分类信息
            category_map = {}
            if images:
                category_ids = list(set(img.category_id for img in images))
                categories = self.db.query(ResourceCategories).filter(
                    ResourceCategories.id.in_(category_ids)
                ).all()
                category_map = {cat.id: cat.category_name for cat in categories}
            
            # 转换为响应格式
            image_responses = []
            for image in images:
                image_dict = ImageResponse.from_orm(image).__dict__
                image_dict['category_name'] = category_map.get(image.category_id)
                image_responses.append(ImageResponse(**image_dict))
            
            # 计算总页数
            pages = (total + size - 1) // size
            
            return ImageListResponse(
                items=image_responses,
                total=total,
                page=page,
                size=size,
                pages=pages
            )
            
        except Exception as e:
            logger.error(f"获取资源图片列表失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"获取资源图片列表失败: {str(e)}",
                data=None
            )
    
    def get_resource_image_detail(self, image_id: int) -> ImageResponse:
        """
        获取图片详情
        
        Args:
            image_id: 图片ID
            
        Returns:
            ImageResponse: 图片详情
        """
        try:
            image = self.db.query(ResourceImages).filter(
                ResourceImages.id == image_id,
                ResourceImages.is_deleted == False
            ).first()
            
            if not image:
                raise BusinessException(
                    code=404,
                    message="图片不存在",
                    data=None
                )
            
            # 获取分类名称
            category = self.db.query(ResourceCategories).filter(
                ResourceCategories.id == image.category_id
            ).first()
            
            image_dict = ImageResponse.from_orm(image).__dict__
            image_dict['category_name'] = category.category_name if category else None
            
            return ImageResponse(**image_dict)
            
        except BusinessException:
            raise
        except Exception as e:
            logger.error(f"获取图片详情失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"获取图片详情失败: {str(e)}",
                data=None
            )
    
    def update_image_status(self, image_id: int, status: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        更新图片状态
        
        Args:
            image_id: 图片ID
            status: 新状态
            reason: 更新原因
            
        Returns:
            Dict: 更新结果
        """
        try:
            image = self.db.query(ResourceImages).filter(
                ResourceImages.id == image_id,
                ResourceImages.is_deleted == False
            ).first()
            
            if not image:
                raise BusinessException(
                    code=404,
                    message="图片不存在",
                    data=None
                )
            
            # 验证状态转换
            if image.usage_status == UsageStatus.used and status == UsageStatus.available:
                raise BusinessException(
                    code=400,
                    message="已使用的图片不能重新设为可用状态",
                    data=None
                )
            
            old_status = image.usage_status
            image.usage_status = getattr(UsageStatus, status)
            image.updated_at = datetime.now()
            
            self.db.commit()
            
            return {
                'image_id': image_id,
                'old_status': old_status.value,
                'new_status': status,
                'reason': reason,
                'updated_at': image.updated_at
            }
            
        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新图片状态失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"更新图片状态失败: {str(e)}",
                data=None
            )
    
    def delete_resource_image(self, image_id: int, delete_reason: Optional[str] = None) -> Dict[str, Any]:
        """
        删除图片（软删除）
        
        Args:
            image_id: 图片ID
            delete_reason: 删除原因
            
        Returns:
            Dict: 删除结果
        """
        try:
            image = self.db.query(ResourceImages).filter(
                ResourceImages.id == image_id,
                ResourceImages.is_deleted == False
            ).first()
            
            if not image:
                raise BusinessException(
                    code=404,
                    message="图片不存在",
                    data=None
                )
            
            # 检查是否为已使用状态，禁止删除已使用的图片
            if image.usage_status == UsageStatus.used:
                raise BusinessException(
                    code=400,
                    message="不能删除已使用的图片",
                    data={
                        'image_id': image_id,
                        'usage_status': image.usage_status.value,
                        'used_in_task_id': image.used_in_task_id
                    }
                )
            
            # 软删除
            image.is_deleted = True
            image.deleted_at = datetime.now()
            image.deleted_reason = delete_reason
            
            # 删除OSS文件（可选，这里先注释掉）
            # oss_client.delete_file(image.file_path)
            
            self.db.commit()
            
            return {
                'image_id': image_id,
                'original_filename': image.original_filename,
                'deleted_at': image.deleted_at,
                'delete_reason': delete_reason
            }
            
        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除图片失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"删除图片失败: {str(e)}",
                data=None
            )
    
    def batch_delete_images(self, image_ids: List[int], delete_reason: Optional[str] = None) -> Dict[str, Any]:
        """
        批量删除图片
        
        Args:
            image_ids: 图片ID列表
            delete_reason: 删除原因
            
        Returns:
            Dict: 删除结果统计
        """
        try:
            # 查询要删除的图片
            images = self.db.query(ResourceImages).filter(
                ResourceImages.id.in_(image_ids),
                ResourceImages.is_deleted == False
            ).all()
            
            if not images:
                raise BusinessException(
                    code=404,
                    message="没有找到可删除的图片",
                    data=None
                )
            
            # 检查是否有已使用的图片
            used_images = [img for img in images if img.usage_status == UsageStatus.used]
            if used_images:
                used_filenames = [img.original_filename for img in used_images]
                raise BusinessException(
                    code=400,
                    message=f"不能删除已使用的图片：{', '.join(used_filenames)}",
                    data={
                        'used_image_ids': [img.id for img in used_images],
                        'used_filenames': used_filenames
                    }
                )
            
            deleted_count = 0
            oss_paths = []
            
            for image in images:
                image.is_deleted = True
                image.deleted_at = datetime.now()
                image.deleted_reason = delete_reason
                oss_paths.append(image.file_path)
                deleted_count += 1
            
            self.db.commit()
            
            # 批量删除OSS文件（可选）
            # if oss_paths:
            #     oss_client.delete_multiple_files(oss_paths)
            
            return {
                'total_requested': len(image_ids),
                'deleted_count': deleted_count,
                'delete_reason': delete_reason,
                'deleted_at': datetime.now()
            }
            
        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量删除图片失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"批量删除图片失败: {str(e)}",
                data=None
            )
    
    def get_available_image_for_task(self, category_code: str) -> AvailableImageResponse:
        """
        为虚拟任务获取可用图片
        
        Args:
            category_code: 分类代码
            
        Returns:
            AvailableImageResponse: 可用图片信息
        """
        try:
            # 查询分类
            category = self.db.query(ResourceCategories).filter(
                ResourceCategories.category_code == category_code,
                ResourceCategories.is_active == True
            ).first()
            
            if not category:
                return AvailableImageResponse(
                    success=False,
                    message=f"分类 {category_code} 不存在或已禁用"
                )
            
            # 查询可用图片
            available_image = self.db.query(ResourceImages).filter(
                ResourceImages.category_id == category.id,
                ResourceImages.usage_status == UsageStatus.available,
                ResourceImages.is_deleted == False
            ).order_by(func.random()).first()  # 随机选择
            
            if not available_image:
                return AvailableImageResponse(
                    success=False,
                    message=f"分类 {category_code} 下没有可用图片"
                )
            
            return AvailableImageResponse(
                success=True,
                image_id=available_image.id,
                file_url=available_image.file_url,
                image_code=available_image.image_code,
                category_code=category_code,
                original_filename=available_image.original_filename
            )
            
        except Exception as e:
            logger.error(f"获取可用图片失败: {str(e)}")
            return AvailableImageResponse(
                success=False,
                message=f"获取可用图片失败: {str(e)}"
            )
    
    def mark_image_as_used(self, image_id: int, task_id: int) -> Dict[str, Any]:
        """
        标记图片已使用

        Args:
            image_id: 图片ID
            task_id: 任务ID

        Returns:
            Dict: 标记结果
        """
        try:
            image = self.db.query(ResourceImages).filter(
                ResourceImages.id == image_id,
                ResourceImages.usage_status == UsageStatus.available,
                ResourceImages.is_deleted == False
            ).first()

            if not image:
                raise BusinessException(
                    code=404,
                    message="图片不存在或不可用",
                    data=None
                )

            # 标记为已使用
            image.usage_status = UsageStatus.used
            image.used_at = datetime.now()
            image.used_in_task_id = task_id
            image.updated_at = datetime.now()

            self.db.commit()

            return {
                'image_id': image_id,
                'task_id': task_id,
                'used_at': image.used_at,
                'file_url': image.file_url
            }

        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"标记图片已使用失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"标记图片已使用失败: {str(e)}",
                data=None
            )

    def get_and_mark_image_as_used(self, category_code: str, task_id: Optional[int] = None) -> AvailableImageResponse:
        """
        获取可用图片并立即标记为已使用（并发安全）

        Args:
            category_code: 分类代码
            task_id: 任务ID（可选）

        Returns:
            AvailableImageResponse: 图片信息和标记结果
        """
        try:
            # 查询分类
            category = self.db.query(ResourceCategories).filter(
                ResourceCategories.category_code == category_code,
                ResourceCategories.is_active == True
            ).first()

            if not category:
                return AvailableImageResponse(
                    success=False,
                    message=f"分类 {category_code} 不存在或已禁用"
                )

            # 使用数据库锁机制，原子性地获取并标记图片
            # 使用 SELECT ... FOR UPDATE 确保并发安全
            available_image = self.db.query(ResourceImages).filter(
                ResourceImages.category_id == category.id,
                ResourceImages.usage_status == UsageStatus.available,
                ResourceImages.is_deleted == False
            ).order_by(func.random()).with_for_update().first()

            if not available_image:
                return AvailableImageResponse(
                    success=False,
                    message=f"分类 {category_code} 下没有可用图片"
                )

            # 立即标记为已使用
            available_image.usage_status = UsageStatus.used
            available_image.used_at = datetime.now()
            available_image.used_in_task_id = task_id
            available_image.updated_at = datetime.now()

            # 提交事务
            self.db.commit()

            return AvailableImageResponse(
                success=True,
                message="成功获取并标记图片",
                image_id=available_image.id,
                image_code=available_image.image_code,
                file_url=available_image.file_url,
                category_code=category_code,
                original_filename=available_image.original_filename,
                used_at=available_image.used_at
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"获取并标记图片失败: {str(e)}")
            return AvailableImageResponse(
                success=False,
                message=f"获取并标记图片失败: {str(e)}"
            )
    
    def get_resource_stats(self) -> ResourceStatsResponse:
        """
        获取资源统计信息
        
        Returns:
            ResourceStatsResponse: 统计信息
        """
        try:
            # 基础统计
            total_images = self.db.query(ResourceImages).filter(
                ResourceImages.is_deleted == False
            ).count()
            
            available_images = self.db.query(ResourceImages).filter(
                ResourceImages.usage_status == UsageStatus.available,
                ResourceImages.is_deleted == False
            ).count()
            
            used_images = self.db.query(ResourceImages).filter(
                ResourceImages.usage_status == UsageStatus.used,
                ResourceImages.is_deleted == False
            ).count()
            
            disabled_images = self.db.query(ResourceImages).filter(
                ResourceImages.usage_status == UsageStatus.disabled,
                ResourceImages.is_deleted == False
            ).count()
            
            # 总文件大小
            total_size_result = self.db.query(func.sum(ResourceImages.file_size)).filter(
                ResourceImages.is_deleted == False
            ).scalar()
            total_size = int(total_size_result) if total_size_result else 0
            
            # 按分类统计 (MySQL兼容语法)
            categories_stats = self.db.query(
                ResourceCategories.category_name,
                func.count(ResourceImages.id).label('count'),
                func.sum(func.if_(ResourceImages.usage_status == UsageStatus.available, 1, 0)).label('available'),
                func.sum(func.if_(ResourceImages.usage_status == UsageStatus.used, 1, 0)).label('used')
            ).outerjoin(ResourceImages, 
                and_(ResourceImages.category_id == ResourceCategories.id, ResourceImages.is_deleted == False)
            ).filter(ResourceCategories.is_active == True).group_by(ResourceCategories.id).all()
            
            categories_list = []
            for stat in categories_stats:
                categories_list.append({
                    'category_name': stat.category_name,
                    'total': stat.count,
                    'available': stat.available,
                    'used': stat.used
                })
            
            # 最近上传
            recent_uploads = self.db.query(
                ResourceImages.original_filename,
                ResourceImages.file_size,
                ResourceImages.created_at,
                ResourceCategories.category_name
            ).join(ResourceCategories).filter(
                ResourceImages.is_deleted == False
            ).order_by(desc(ResourceImages.created_at)).limit(10).all()
            
            recent_list = []
            for upload in recent_uploads:
                recent_list.append({
                    'filename': upload.original_filename,
                    'file_size': upload.file_size,
                    'category_name': upload.category_name,
                    'created_at': upload.created_at.isoformat()
                })
            
            return ResourceStatsResponse(
                total_images=total_images,
                available_images=available_images,
                used_images=used_images,
                disabled_images=disabled_images,
                total_size=total_size,
                categories_stats=categories_list,
                recent_uploads=recent_list
            )
            
        except Exception as e:
            logger.error(f"获取资源统计失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"获取资源统计失败: {str(e)}",
                data=None
            )
    
    def _generate_batch_code(self) -> str:
        """生成批次编号"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"BATCH_{timestamp}_{unique_id}"
    
    def _generate_image_code(self) -> str:
        """生成图片编号"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"IMG_{timestamp}_{unique_id}"
    
    def get_category_detailed_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取三类资源的详细统计信息
        
        Returns:
            Dict: 包含avatar_redesign, room_decoration, photo_extension三类的详细统计
        """
        try:
            # 定义三类资源的category_code
            target_categories = ['avatar_redesign', 'room_decoration', 'photo_extension']
            
            # 查询这三类分类的ID映射
            categories = self.db.query(ResourceCategories).filter(
                ResourceCategories.category_code.in_(target_categories),
                ResourceCategories.is_active == True
            ).all()
            
            category_id_map = {cat.category_code: cat.id for cat in categories}
            
            # 初始化结果字典
            result = {}
            for category_code in target_categories:
                result[category_code] = {
                    'total': 0,
                    'available': 0,
                    'used': 0,
                    'rate': 0.0
                }
            
            # 只处理存在的分类
            if category_id_map:
                # 查询统计数据
                stats_query = self.db.query(
                    ResourceCategories.category_code,
                    func.count(ResourceImages.id).label('total'),
                    func.sum(func.if_(ResourceImages.usage_status == UsageStatus.available, 1, 0)).label('available'),
                    func.sum(func.if_(ResourceImages.usage_status == UsageStatus.used, 1, 0)).label('used')
                ).outerjoin(ResourceImages, 
                    and_(
                        ResourceImages.category_id == ResourceCategories.id, 
                        ResourceImages.is_deleted == False
                    )
                ).filter(
                    ResourceCategories.id.in_(list(category_id_map.values()))
                ).group_by(ResourceCategories.id, ResourceCategories.category_code).all()
                
                # 处理查询结果
                for stat in stats_query:
                    category_code = stat.category_code
                    total = stat.total or 0
                    available = stat.available or 0
                    used = stat.used or 0
                    
                    # 计算使用率
                    rate = round((used / max(total, 1)) * 100, 2) if total > 0 else 0.0
                    
                    result[category_code] = {
                        'total': total,
                        'available': available,
                        'used': used,
                        'rate': rate
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"获取分类详细统计失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"获取分类详细统计失败: {str(e)}",
                data=None
            )
    
    def batch_move_category(
        self, 
        image_ids: List[int], 
        target_category_id: int, 
        move_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量移动图片到指定分类
        
        Args:
            image_ids: 图片ID列表
            target_category_id: 目标分类ID
            move_reason: 移动原因
            
        Returns:
            Dict: 移动结果统计
        """
        try:
            # 验证目标分类是否存在
            target_category = self.db.query(ResourceCategories).filter(
                ResourceCategories.id == target_category_id,
                ResourceCategories.is_active == True
            ).first()
            
            if not target_category:
                raise BusinessException(
                    code=404,
                    message="目标分类不存在或已禁用",
                    data=None
                )
            
            # 查询要移动的图片
            images = self.db.query(ResourceImages).filter(
                ResourceImages.id.in_(image_ids),
                ResourceImages.is_deleted == False
            ).all()
            
            if not images:
                raise BusinessException(
                    code=404,
                    message="没有找到可移动的图片",
                    data=None
                )
            
            moved_count = 0
            skipped_count = 0
            
            for image in images:
                # 检查图片是否已经在目标分类中
                if image.category_id == target_category_id:
                    skipped_count += 1
                    continue
                
                # 更新分类
                old_category_id = image.category_id
                image.category_id = target_category_id
                image.updated_at = datetime.now()
                
                moved_count += 1
                
                logger.info(f"图片 {image.id} 从分类 {old_category_id} 移动到分类 {target_category_id}")
            
            # 提交数据库更改
            self.db.commit()
            
            logger.info(f"批量移动分类成功: 移动 {moved_count} 张图片到分类 {target_category.category_name}")
            
            return {
                "total_requested": len(image_ids),
                "moved_count": moved_count,
                "skipped_count": skipped_count,
                "target_category": {
                    "id": target_category.id,
                    "name": target_category.category_name
                },
                "move_reason": move_reason
            }
            
        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量移动分类失败: {str(e)}")
            raise BusinessException(
                code=500,
                message=f"批量移动分类失败: {str(e)}",
                data=None
            )