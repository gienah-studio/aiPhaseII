import pandas as pd
import io
from typing import List, Dict, Any, Tuple
from fastapi import UploadFile, HTTPException
from decimal import Decimal

class ExcelProcessor:
    """Excel文件处理工具类"""
    
    @staticmethod
    async def read_excel_file(file: UploadFile) -> pd.DataFrame:
        """读取Excel文件"""
        try:
            # 检查文件类型
            if not file.filename.endswith(('.xlsx', '.xls')):
                raise HTTPException(status_code=400, detail="文件格式不支持，请上传Excel文件")
            
            # 读取文件内容
            content = await file.read()
            
            # 使用pandas读取Excel
            df = pd.read_excel(io.BytesIO(content))
            
            return df
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"读取Excel文件失败: {str(e)}")
    
    @staticmethod
    def validate_student_subsidy_data(df: pd.DataFrame) -> Tuple[List[Dict], List[str], int]:
        """验证学生补贴数据"""
        valid_data = []
        errors = []
        filtered_count = 0  # 记录被过滤的记录数量
        
        # 检查必需的列
        required_columns = ['学生姓名', '补贴金额']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Excel文件缺少必需的列: {', '.join(missing_columns)}"
            )
        
        for index, row in df.iterrows():
            try:
                # 验证学生姓名
                student_name = str(row['学生姓名']).strip()
                if not student_name or student_name == 'nan':
                    errors.append(f"第{index+2}行: 学生姓名不能为空")
                    continue
                
                # 验证补贴金额
                try:
                    subsidy_amount = float(row['补贴金额'])
                    if subsidy_amount < 0:
                        # 只过滤负数，允许0元补贴（用于隐藏学生）
                        filtered_count += 1
                        continue
                except (ValueError, TypeError):
                    errors.append(f"第{index+2}行: 补贴金额格式不正确")
                    continue
                
                valid_data.append({
                    'student_name': student_name,
                    'subsidy_amount': Decimal(str(subsidy_amount))
                })
                
            except Exception as e:
                errors.append(f"第{index+2}行: 数据处理错误 - {str(e)}")
        
        return valid_data, errors, filtered_count
    
    @staticmethod
    def validate_customer_service_data(df: pd.DataFrame) -> Tuple[List[Dict], List[str]]:
        """验证专用客服数据"""
        valid_data = []
        errors = []
        
        # 检查必需的列（根据实际需求调整）
        required_columns = ['姓名', '账号']  # 可以根据需要添加更多字段
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Excel文件缺少必需的列: {', '.join(missing_columns)}"
            )
        
        for index, row in df.iterrows():
            try:
                # 验证姓名
                name = str(row['姓名']).strip()
                if not name or name == 'nan':
                    errors.append(f"第{index+2}行: 姓名不能为空")
                    continue
                
                # 验证账号
                account = str(row['账号']).strip()
                if not account or account == 'nan':
                    errors.append(f"第{index+2}行: 账号不能为空")
                    continue
                
                # 可以添加更多字段验证
                valid_data.append({
                    'name': name,
                    'account': account,
                    'phone_number': str(row.get('手机号', '')).strip() if pd.notna(row.get('手机号')) else None,
                    'id_card': str(row.get('身份证号', '')).strip() if pd.notna(row.get('身份证号')) else None,
                })
                
            except Exception as e:
                errors.append(f"第{index+2}行: 数据处理错误 - {str(e)}")
        
        return valid_data, errors
    
    @staticmethod
    def generate_excel_report(data: List[Dict[str, Any]], filename: str) -> bytes:
        """生成Excel报表"""
        try:
            df = pd.DataFrame(data)
            
            # 创建Excel文件
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='虚拟订单报表', index=False)
            
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"生成Excel报表失败: {str(e)}")
    
    @staticmethod
    def validate_excel_file_size(file: UploadFile, max_size_mb: int = 10):
        """验证Excel文件大小"""
        if file.size > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400, 
                detail=f"文件大小超过限制，最大允许{max_size_mb}MB"
            )
