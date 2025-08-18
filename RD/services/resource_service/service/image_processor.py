import io
import zipfile
import hashlib
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """图片处理和分析工具"""
    
    # 支持的图片格式
    SUPPORTED_IMAGE_FORMATS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'
    }
    
    # 支持的MIME类型
    SUPPORTED_MIME_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 
        'image/webp', 'image/tiff', 'image/x-ms-bmp'
    }
    
    # 文件大小限制（字节）
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_ZIP_SIZE = 200 * 1024 * 1024  # 200MB
    
    # 图片尺寸限制
    MAX_IMAGE_WIDTH = 8192
    MAX_IMAGE_HEIGHT = 8192
    MIN_IMAGE_WIDTH = 100
    MIN_IMAGE_HEIGHT = 100
    
    @staticmethod
    def is_zip_file(file_content: bytes) -> bool:
        """
        检查文件是否为ZIP格式
        
        Args:
            file_content: 文件内容
            
        Returns:
            bool: 是否为ZIP文件
        """
        try:
            # 检查ZIP文件头
            if len(file_content) < 4:
                return False
            
            # ZIP文件的魔数
            zip_signatures = [
                b'PK\x03\x04',  # 标准ZIP
                b'PK\x05\x06',  # 空ZIP
                b'PK\x07\x08'   # 跨卷ZIP
            ]
            
            file_header = file_content[:4]
            return any(file_header.startswith(sig) for sig in zip_signatures)
            
        except Exception as e:
            logger.error(f"检查ZIP文件格式失败: {str(e)}")
            return False
    
    @staticmethod
    def extract_zip_files(zip_content: bytes) -> List[Dict[str, Any]]:
        """
        解压ZIP文件并提取图片
        
        Args:
            zip_content: ZIP文件内容
            
        Returns:
            List[Dict]: 提取的图片文件列表
        """
        extracted_files = []
        
        try:
            # 检查ZIP文件大小
            if len(zip_content) > ImageProcessor.MAX_ZIP_SIZE:
                raise ValueError(f"ZIP文件过大，最大支持{ImageProcessor.MAX_ZIP_SIZE // 1024 // 1024}MB")
            
            # 打开ZIP文件
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_file:
                # 获取ZIP文件信息
                file_list = zip_file.namelist()
                
                if len(file_list) > 1000:  # 限制单个ZIP包含的文件数量
                    raise ValueError("ZIP文件包含的文件数量过多，最大支持1000个文件")
                
                for filename in file_list:
                    try:
                        # 跳过目录和隐藏文件
                        if filename.endswith('/') or filename.startswith('.'):
                            continue
                        
                        # 跳过__MACOSX等系统文件夹
                        if '__MACOSX' in filename or '.DS_Store' in filename:
                            continue
                        
                        # 检查文件扩展名
                        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
                        if file_ext not in ImageProcessor.SUPPORTED_IMAGE_FORMATS:
                            logger.warning(f"跳过不支持的文件格式: {filename}")
                            continue
                        
                        # 读取文件内容
                        file_content = zip_file.read(filename)
                        
                        # 检查文件大小
                        if len(file_content) > ImageProcessor.MAX_FILE_SIZE:
                            logger.warning(f"跳过过大的文件: {filename}")
                            continue
                        
                        # 验证是否为有效图片
                        if ImageProcessor.validate_image_format(file_content):
                            extracted_files.append({
                                'filename': filename,
                                'content': file_content,
                                'size': len(file_content)
                            })
                        else:
                            logger.warning(f"跳过无效的图片文件: {filename}")
                    
                    except Exception as e:
                        logger.error(f"处理ZIP文件中的 {filename} 失败: {str(e)}")
                        continue
                
        except zipfile.BadZipFile:
            raise ValueError("无效的ZIP文件格式")
        except Exception as e:
            logger.error(f"解压ZIP文件失败: {str(e)}")
            raise ValueError(f"解压ZIP文件失败: {str(e)}")
        
        if not extracted_files:
            raise ValueError("ZIP文件中没有找到有效的图片文件")
        
        logger.info(f"从ZIP文件中提取了 {len(extracted_files)} 个有效图片")
        return extracted_files
    
    @staticmethod
    def validate_image_format(file_content: bytes) -> bool:
        """
        验证文件是否为有效的图片格式
        
        Args:
            file_content: 文件内容
            
        Returns:
            bool: 是否为有效图片
        """
        try:
            if len(file_content) == 0:
                return False
            
            # 使用PIL验证图片
            with Image.open(io.BytesIO(file_content)) as img:
                # 验证图片格式
                if img.format.lower() not in ['jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff']:
                    return False
                
                # 验证图片尺寸
                width, height = img.size
                if (width < ImageProcessor.MIN_IMAGE_WIDTH or 
                    height < ImageProcessor.MIN_IMAGE_HEIGHT or
                    width > ImageProcessor.MAX_IMAGE_WIDTH or 
                    height > ImageProcessor.MAX_IMAGE_HEIGHT):
                    return False
                
                # 尝试验证图片是否损坏
                img.verify()
                return True
                
        except Exception as e:
            logger.debug(f"图片验证失败: {str(e)}")
            return False
    
    @staticmethod
    def get_image_info(file_content: bytes) -> Dict[str, Any]:
        """
        获取图片详细信息
        
        Args:
            file_content: 图片文件内容
            
        Returns:
            Dict: 图片信息
        """
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                # 基本信息
                info = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size': len(file_content),
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
                
                # 尝试获取EXIF信息
                try:
                    exif_data = img._getexif()
                    if exif_data:
                        info['exif'] = {
                            'make': exif_data.get(271),  # 制造商
                            'model': exif_data.get(272),  # 型号
                            'datetime': exif_data.get(306),  # 拍摄时间
                            'orientation': exif_data.get(274)  # 方向
                        }
                except:
                    info['exif'] = None
                
                # 计算质量评分（基于分辨率、文件大小等）
                info['quality_score'] = ImageProcessor._calculate_quality_score(
                    img.width, img.height, len(file_content)
                )
                
                return info
                
        except Exception as e:
            logger.error(f"获取图片信息失败: {str(e)}")
            return {
                'width': 0,
                'height': 0,
                'format': 'unknown',
                'mode': 'unknown',
                'size': len(file_content),
                'quality_score': 0.0,
                'error': str(e)
            }
    
    @staticmethod
    def calculate_file_hash(file_content: bytes) -> str:
        """
        计算文件MD5哈希值
        
        Args:
            file_content: 文件内容
            
        Returns:
            str: MD5哈希值
        """
        try:
            return hashlib.md5(file_content).hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败: {str(e)}")
            return ""
    
    @staticmethod
    def get_content_type(filename: str) -> str:
        """
        根据文件名获取MIME类型
        
        Args:
            filename: 文件名
            
        Returns:
            str: MIME类型
        """
        content_type, _ = mimetypes.guess_type(filename)
        
        # 如果无法推测，根据扩展名手动判断
        if not content_type:
            ext = filename.lower().split('.')[-1] if '.' in filename else ''
            content_type_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'bmp': 'image/bmp',
                'webp': 'image/webp',
                'tiff': 'image/tiff',
                'tif': 'image/tiff'
            }
            content_type = content_type_map.get(ext, 'application/octet-stream')
        
        return content_type
    
    @staticmethod
    def resize_if_needed(file_content: bytes, max_width: int = 2048, 
                        max_height: int = 2048, quality: int = 85) -> bytes:
        """
        如果图片尺寸过大则进行压缩
        
        Args:
            file_content: 原始图片内容
            max_width: 最大宽度
            max_height: 最大高度
            quality: JPEG质量
            
        Returns:
            bytes: 处理后的图片内容
        """
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                # 检查是否需要调整尺寸
                if img.width <= max_width and img.height <= max_height:
                    return file_content
                
                # 计算新尺寸（保持宽高比）
                ratio = min(max_width / img.width, max_height / img.height)
                new_width = int(img.width * ratio)
                new_height = int(img.height * ratio)
                
                # 调整尺寸
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 保存到内存
                output = io.BytesIO()
                
                # 根据原格式保存
                if img.format == 'PNG' and resized_img.mode in ('RGBA', 'LA'):
                    resized_img.save(output, format='PNG', optimize=True)
                else:
                    # 转换为RGB并保存为JPEG
                    if resized_img.mode in ('RGBA', 'LA'):
                        rgb_img = Image.new('RGB', resized_img.size, (255, 255, 255))
                        rgb_img.paste(resized_img, mask=resized_img.split()[-1] if resized_img.mode == 'RGBA' else None)
                        resized_img = rgb_img
                    
                    resized_img.save(output, format='JPEG', quality=quality, optimize=True)
                
                compressed_content = output.getvalue()
                
                # 如果压缩后反而更大，返回原图
                if len(compressed_content) >= len(file_content):
                    return file_content
                
                logger.info(f"图片已压缩: {len(file_content)} -> {len(compressed_content)} bytes")
                return compressed_content
                
        except Exception as e:
            logger.error(f"图片压缩失败: {str(e)}")
            return file_content
    
    @staticmethod
    def _calculate_quality_score(width: int, height: int, file_size: int) -> float:
        """
        计算图片质量评分
        
        Args:
            width: 图片宽度
            height: 图片高度
            file_size: 文件大小
            
        Returns:
            float: 质量评分 (0-10)
        """
        try:
            # 基于分辨率的评分
            resolution_score = min(10, (width * height) / (1920 * 1080) * 5)
            
            # 基于文件大小的评分（避免过小的文件）
            size_score = min(5, file_size / (500 * 1024) * 3)  # 500KB作为基准
            
            # 综合评分
            total_score = (resolution_score + size_score) / 2
            
            return round(min(10.0, max(0.0, total_score)), 2)
            
        except Exception:
            return 5.0  # 默认评分