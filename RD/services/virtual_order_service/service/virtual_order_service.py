from datetime import datetime, timedelta
import random
from typing import List, Dict, Any, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from nanoid import generate

from shared.models.virtual_order_pool import VirtualOrderPool
from shared.models.virtual_order_reports import VirtualOrderReports
from shared.models.tasks import Tasks
from shared.models.userinfo import UserInfo
from shared.models.original_user import OriginalUser
from shared.exceptions import BusinessException
from ..utils.excel_utils import ExcelProcessor

class VirtualOrderService:
    """虚拟订单服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        # nanoid字符集（对应JS的customAlphabet('1234567890abcdef', 10)）
        self.nanoid_alphabet = '1234567890abcdef'
        self.nanoid_length = 10
        
        # 任务内容随机生成配置
        self.task_adjectives = [
            '紧急', '重要', '优先', '高效', '精准', '快速', '专业', '优质',
            '关键', '核心', '特殊', '标准', '规范', '详细', '完整', '准确'
        ]

        self.task_actions = [
            '整理', '分析', '处理', '核查', '审核', '统计', '汇总', '编辑',
            '校对', '归档', '分类', '筛选', '验证', '确认', '更新', '维护'
        ]

        self.task_requirements = [
            '请按照标准流程完成相关工作，注意保持高质量标准。',
            '请仔细核对相关信息，确保准确性和完整性。',
            '请按照既定规范进行操作，保证工作效率。',
            '请认真完成指定内容，注意细节处理。',
            '请严格按照要求执行，确保符合质量标准。',
            '请高效完成相关任务，保持专业水准。'
        ]

        # 任务模板配置（后续可以从配置文件或数据库读取）
        self.task_templates = {
            'source': '集团业务',  # 可选：淘宝、集团业务、其他业务
            'commission_unit': '人民币',
            'task_style': '数据处理',
            'task_type': '虚拟任务',
            'reference_images': '',
            'founder': '虚拟订单系统',
            'founder_id': 0,
            'orders_number': 1,
            'order_received_number': 0,
            'status': '0',  # 修改为数字状态
            'payment_status': '0',  # 待支付
            'task_level': 'D',  # 修改为D级别
            'end_date_hours': 3,  # 接单截止时间：创建后3小时
            'delivery_date_days': 3,  # 交稿时间：接单后3天
        }
    
    def generate_order_number(self) -> str:
        """生成订单号"""
        return generate(self.nanoid_alphabet, self.nanoid_length)

    def generate_random_task_content(self) -> Dict[str, str]:
        """
        生成随机的任务内容

        Returns:
            Dict[str, str]: 包含summary和requirement的字典
        """
        # 随机选择形容词和动作
        adjective = random.choice(self.task_adjectives)
        action = random.choice(self.task_actions)
        requirement = random.choice(self.task_requirements)

        # 生成任务标题
        summary = f'{adjective}任务 - {action}工作'

        return {
            'summary': summary,
            'requirement': requirement
        }
    
    def calculate_task_amounts(self, total_amount: Decimal) -> List[Decimal]:
        """
        计算任务金额分配

        Args:
            total_amount: 总补贴金额

        Returns:
            List[Decimal]: 任务金额列表
        """
        amounts = []
        remaining = total_amount

        # 如果金额小于等于5，直接返回一个任务
        if remaining <= 5:
            return [remaining]

        # 最小单位5元，最大单位25元
        min_amount = Decimal('5')
        max_amount = Decimal('25')

        # 固定的金额选项：5, 10, 15, 20, 25
        available_amounts = [Decimal('5'), Decimal('10'), Decimal('15'), Decimal('20'), Decimal('25')]

        # 随机生成5-25之间的5的倍数任务
        while remaining > 0:
            if remaining <= min_amount:
                # 剩余金额小于等于5元，作为最后一个任务
                amounts.append(remaining)
                break
            elif remaining < min_amount * 2:
                # 剩余金额小于10元，直接作为一个任务
                amounts.append(remaining)
                break
            else:
                # 从可用金额中筛选不超过剩余金额的选项
                possible_amounts = [amount for amount in available_amounts if amount <= remaining]

                if not possible_amounts:
                    # 如果没有合适的金额选项，使用剩余金额
                    amounts.append(remaining)
                    break

                # 随机选择一个金额
                selected_amount = random.choice(possible_amounts)
                amounts.append(selected_amount)
                remaining -= selected_amount

        return amounts
    
    def create_virtual_task(self, student_id: int, student_name: str, amount: Decimal) -> Tasks:
        """
        创建单个虚拟任务

        Args:
            student_id: 学生ID
            student_name: 学生姓名
            amount: 任务金额

        Returns:
            Tasks: 创建的任务对象
        """
        now = datetime.now()

        # 生成随机任务内容
        task_content = self.generate_random_task_content()

        task = Tasks(
            summary=task_content['summary'],
            requirement=task_content['requirement'],
            reference_images=self.task_templates['reference_images'],
            source=self.task_templates['source'],
            order_number=self.generate_order_number(),
            commission=amount,
            commission_unit=self.task_templates['commission_unit'],
            end_date=now + timedelta(hours=self.task_templates['end_date_hours']),  # 3小时后过期
            delivery_date=now + timedelta(days=self.task_templates['delivery_date_days']),
            status=self.task_templates['status'],
            task_style=self.task_templates['task_style'],
            task_type=self.task_templates['task_type'],
            created_at=now,
            updated_at=now,
            orders_number=self.task_templates['orders_number'],
            order_received_number=self.task_templates['order_received_number'],
            founder=self.task_templates['founder'],
            founder_id=self.task_templates['founder_id'],
            payment_status=self.task_templates['payment_status'],
            task_level=self.task_templates['task_level'],
            is_virtual=True,  # 标识为虚拟任务
            is_renew='0',
            target_student_id=student_id  # 限制只有指定学生可以接取
        )

        return task
    
    def generate_virtual_tasks_for_student(self, student_id: int, student_name: str, 
                                         subsidy_amount: Decimal) -> List[Tasks]:
        """
        为学生生成虚拟任务
        
        Args:
            student_id: 学生ID
            student_name: 学生姓名
            subsidy_amount: 补贴金额
            
        Returns:
            List[Tasks]: 生成的任务列表
        """
        # 计算任务金额分配
        task_amounts = self.calculate_task_amounts(subsidy_amount)
        
        # 创建任务
        tasks = []
        for amount in task_amounts:
            task = self.create_virtual_task(student_id, student_name, amount)
            tasks.append(task)
        
        return tasks

    def import_student_subsidy_data(self, student_data: List[Dict], import_batch: str) -> Dict[str, Any]:
        """
        导入学生补贴数据并生成虚拟任务

        Args:
            student_data: 学生数据列表
            import_batch: 导入批次号

        Returns:
            Dict: 导入结果统计
        """
        try:
            total_students = 0
            total_subsidy = Decimal('0')
            total_generated_tasks = 0

            for data in student_data:
                student_name = data['student_name']
                subsidy_amount = data['subsidy_amount']

                # 查找学生ID（这里需要根据实际业务逻辑调整）
                # 暂时使用学生姓名作为标识，实际应该有更准确的匹配方式
                student_info = self.db.query(UserInfo).filter(
                    UserInfo.name == student_name,
                    UserInfo.level == '3',  # 学生级别
                    UserInfo.isDeleted == False
                ).first()

                if not student_info:
                    # 如果找不到学生，可以选择跳过或创建新记录
                    # 这里暂时跳过
                    continue

                # 检查是否已存在该学生的补贴池
                existing_pool = self.db.query(VirtualOrderPool).filter(
                    VirtualOrderPool.student_id == student_info.roleId
                ).first()

                if existing_pool:
                    # 更新现有补贴池
                    existing_pool.total_subsidy += subsidy_amount
                    existing_pool.remaining_amount += subsidy_amount
                    existing_pool.import_batch = import_batch
                    existing_pool.updated_at = datetime.now()
                    existing_pool.last_allocation_at = datetime.now()
                else:
                    # 创建新的补贴池
                    pool = VirtualOrderPool(
                        student_id=student_info.roleId,
                        student_name=student_name,
                        total_subsidy=subsidy_amount,
                        remaining_amount=subsidy_amount,
                        allocated_amount=Decimal('0'),
                        completed_amount=Decimal('0'),
                        status='active',
                        import_batch=import_batch,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        last_allocation_at=datetime.now()
                    )
                    self.db.add(pool)

                # 生成虚拟任务
                tasks = self.generate_virtual_tasks_for_student(
                    student_info.roleId, student_name, subsidy_amount
                )

                # 保存任务到数据库
                for task in tasks:
                    self.db.add(task)

                # 更新补贴池的已分配金额
                if existing_pool:
                    existing_pool.allocated_amount += subsidy_amount
                    existing_pool.remaining_amount = Decimal('0')  # 全部分配完毕
                else:
                    # 新创建的池，更新已分配金额
                    pool.allocated_amount = subsidy_amount
                    pool.remaining_amount = Decimal('0')  # 全部分配完毕

                # 更新补贴池的已分配金额
                # allocated_amount = 总补贴 - 剩余金额
                if existing_pool:
                    existing_pool.allocated_amount = existing_pool.total_subsidy - existing_pool.remaining_amount
                else:
                    pool.allocated_amount = pool.total_subsidy - pool.remaining_amount

                total_students += 1
                total_subsidy += subsidy_amount
                total_generated_tasks += len(tasks)

            # 提交事务
            self.db.commit()

            return {
                'import_batch': import_batch,
                'total_students': total_students,
                'total_subsidy': float(total_subsidy),
                'generated_tasks': total_generated_tasks
            }

        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"导入学生补贴数据失败: {str(e)}",
                data=None
            )

    def import_customer_service_data(self, cs_data: List[Dict]) -> Dict[str, Any]:
        """
        导入专用客服数据

        Args:
            cs_data: 客服数据列表

        Returns:
            Dict: 导入结果统计
        """
        try:
            total_imported = 0
            failed_count = 0
            failed_details = []

            for data in cs_data:
                try:
                    name = data['name']
                    account = data['account']

                    # 检查账号是否已存在
                    existing_user = self.db.query(OriginalUser).filter(
                        OriginalUser.username == account,
                        OriginalUser.isDeleted == False
                    ).first()

                    if existing_user:
                        failed_count += 1
                        failed_details.append(f"账号 {account} 已存在")
                        continue

                    # 创建用户账号
                    user = OriginalUser(
                        username=account,
                        password='$2b$12$defaultpasswordhash',  # 默认密码，需要后续修改
                        role='customer_service',
                        lastLoginTime=None,
                        isDeleted=False
                    )
                    self.db.add(user)
                    self.db.flush()  # 获取用户ID

                    # 创建用户信息
                    user_info = UserInfo(
                        userId=user.id,
                        name=name,
                        account=account,
                        phone_number=data.get('phone_number'),
                        id_card=data.get('id_card'),
                        level='6',  # 虚拟订单专用客服级别
                        parentId=12,  # 归属于管理员账号
                        needsComputer='否',  # 虚拟客服不需要电脑
                        isDeleted=False
                    )
                    self.db.add(user_info)

                    total_imported += 1

                except Exception as e:
                    failed_count += 1
                    failed_details.append(f"导入 {data.get('name', '未知')} 失败: {str(e)}")

            # 提交事务
            self.db.commit()

            return {
                'total_imported': total_imported,
                'failed_count': failed_count,
                'failed_details': failed_details if failed_details else None
            }

        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"导入专用客服数据失败: {str(e)}",
                data=None
            )

    def get_virtual_order_stats(self) -> Dict[str, Any]:
        """获取虚拟订单统计信息"""
        try:
            # 统计学生数量
            total_students = self.db.query(VirtualOrderPool).count()

            # 统计总补贴金额
            total_subsidy_result = self.db.query(func.sum(VirtualOrderPool.total_subsidy)).scalar()
            total_subsidy = float(total_subsidy_result) if total_subsidy_result else 0.0

            # 统计生成的任务数量
            total_tasks_generated = self.db.query(Tasks).filter(Tasks.is_virtual.is_(True)).count()

            # 统计完成的任务数量 (status=4表示已完成)
            total_tasks_completed = self.db.query(Tasks).filter(
                and_(Tasks.is_virtual.is_(True), Tasks.status == '4')
            ).count()

            # 计算完成率
            completion_rate = (total_tasks_completed / total_tasks_generated * 100) if total_tasks_generated > 0 else 0.0

            return {
                'total_students': total_students,
                'total_subsidy': total_subsidy,
                'total_tasks_generated': total_tasks_generated,
                'total_tasks_completed': total_tasks_completed,
                'completion_rate': round(completion_rate, 2)
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取虚拟订单统计失败: {str(e)}",
                data=None
            )

    def get_student_pools(self, page: int = 1, size: int = 20, status: str = None) -> Dict[str, Any]:
        """获取学生补贴池列表"""
        try:
            query = self.db.query(VirtualOrderPool)

            # 状态过滤
            if status:
                query = query.filter(VirtualOrderPool.status == status)

            # 总数统计
            total = query.count()

            # 分页查询
            offset = (page - 1) * size
            pools = query.offset(offset).limit(size).all()

            # 转换为字典格式
            items = []
            for pool in pools:
                # 自动同步该学生的已完成任务金额
                self._sync_student_completed_amount(pool)

                items.append({
                    'id': pool.id,
                    'student_id': pool.student_id,
                    'student_name': pool.student_name,
                    'total_subsidy': float(pool.total_subsidy),
                    'remaining_amount': float(pool.remaining_amount),
                    'allocated_amount': float(pool.allocated_amount),
                    'completed_amount': float(pool.completed_amount),
                    'status': pool.status,
                    'import_batch': pool.import_batch,
                    'created_at': pool.created_at,
                    'last_allocation_at': pool.last_allocation_at
                })

            return {
                'items': items,
                'total': total,
                'page': page,
                'size': size
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取学生补贴池列表失败: {str(e)}",
                data=None
            )

    def _sync_student_completed_amount(self, pool: VirtualOrderPool) -> None:
        """
        同步单个学生的已完成任务金额

        Args:
            pool: 学生补贴池对象
        """
        try:
            # 查询该学生所有已完成的虚拟任务
            completed_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.target_student_id == pool.student_id,
                    Tasks.status == '4'  # 已完成状态
                )
            ).all()

            # 计算实际已完成金额
            actual_completed_amount = sum(task.commission for task in completed_tasks)

            # 如果金额不一致，更新补贴池
            if pool.completed_amount != actual_completed_amount:
                pool.completed_amount = actual_completed_amount

                # 重新计算剩余金额和已分配金额
                pool.remaining_amount = pool.total_subsidy - pool.completed_amount
                pool.allocated_amount = pool.total_subsidy - pool.remaining_amount

                # 确保剩余金额不为负数
                if pool.remaining_amount < 0:
                    pool.remaining_amount = Decimal('0')
                    pool.allocated_amount = pool.total_subsidy

                pool.updated_at = datetime.now()
                self.db.commit()

        except Exception as e:
            # 同步失败不影响主流程，只记录错误
            print(f"同步学生 {pool.student_id} 完成金额失败: {str(e)}")

    def reallocate_student_tasks(self, student_id: int) -> Dict[str, Any]:
        """重新分配学生任务"""
        try:
            # 获取学生补贴池
            pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == student_id
            ).first()

            if not pool:
                raise BusinessException(
                    code=404,
                    message="未找到该学生的补贴池",
                    data=None
                )

            if pool.remaining_amount <= 0:
                raise BusinessException(
                    code=400,
                    message="该学生没有剩余金额可分配",
                    data=None
                )

            # 删除该学生未接取的虚拟任务
            self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.target_student_id == student_id,
                    Tasks.status == '0'  # 修改为数字状态
                )
            ).delete()

            # 重新生成任务
            tasks = self.generate_virtual_tasks_for_student(
                student_id, pool.student_name, pool.remaining_amount
            )

            # 保存新任务
            for task in tasks:
                self.db.add(task)

            # 更新补贴池信息
            # allocated_amount = 总补贴 - 剩余金额
            pool.allocated_amount = pool.total_subsidy - pool.remaining_amount
            pool.last_allocation_at = datetime.now()
            pool.updated_at = datetime.now()

            self.db.commit()

            return {
                'student_id': student_id,
                'remaining_amount': float(pool.remaining_amount),
                'new_tasks_count': len(tasks)
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"重新分配学生任务失败: {str(e)}",
                data=None
            )

    def create_virtual_customer_service(self, name: str, account: str, initial_password: str = "123456") -> Dict[str, Any]:
        """
        创建虚拟订单专用客服

        Args:
            name: 客服姓名
            account: 客服账号
            initial_password: 初始密码（默认123456）

        Returns:
            Dict: 创建结果
        """
        try:
            from shared.models.virtual_customer_service import VirtualCustomerService

            # 检查账号是否已存在（在user表中）
            existing_user = self.db.query(OriginalUser).filter(
                OriginalUser.username == account,
                OriginalUser.isDeleted == False
            ).first()

            if existing_user:
                raise BusinessException(
                    code=400,
                    message=f"账号 {account} 已存在",
                    data=None
                )

            # 检查虚拟客服账号是否已存在
            existing_cs = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.account == account,
                VirtualCustomerService.is_deleted == False
            ).first()

            if existing_cs:
                raise BusinessException(
                    code=400,
                    message=f"虚拟客服账号 {account} 已存在",
                    data=None
                )

            # 对密码进行哈希处理
            import bcrypt
            salt = bcrypt.gensalt(rounds=10)
            hashed_password = bcrypt.hashpw(initial_password.encode('utf-8'), salt).decode('utf-8')

            # 创建用户账号
            user = OriginalUser(
                username=account,
                password=hashed_password,
                role='4',  # 虚拟客服角色设置为4
                lastLoginTime=None,
                isDeleted=False
            )
            self.db.add(user)
            self.db.flush()  # 获取用户ID

            # 创建虚拟客服记录 - initial_password也使用加密密码
            virtual_cs = VirtualCustomerService(
                user_id=user.id,
                name=name,
                account=account,
                initial_password=hashed_password,  # 存储加密后的密码，而不是明文
                level='6',
                status='active',
                is_deleted=False
            )
            self.db.add(virtual_cs)

            # 提交事务
            self.db.commit()

            return {
                'id': virtual_cs.id,
                'user_id': user.id,
                'name': name,
                'account': account,
                'level': '6',
                'status': 'active',
                'initial_password': initial_password  # 仍返回明文密码供前端显示，但数据库存储的是加密密码
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"创建虚拟客服失败: {str(e)}",
                data=None
            )

    def get_virtual_customer_services(self, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取虚拟客服列表"""
        try:
            from shared.models.virtual_customer_service import VirtualCustomerService

            # 查询虚拟客服
            query = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.is_deleted == False
            )

            # 总数统计
            total = query.count()

            # 分页查询
            offset = (page - 1) * size
            customer_services = query.offset(offset).limit(size).all()

            # 转换为字典格式
            items = []
            for cs in customer_services:
                # 获取关联的用户信息
                user = self.db.query(OriginalUser).filter(
                    OriginalUser.id == cs.user_id,
                    OriginalUser.isDeleted == False
                ).first()

                items.append({
                    'id': cs.id,
                    'user_id': cs.user_id,
                    'name': cs.name,
                    'account': cs.account,
                    'level': cs.level,
                    'status': cs.status,
                    'last_login_time': user.lastLoginTime if user else None,
                    'created_at': cs.created_at
                })

            return {
                'items': items,
                'total': total,
                'page': page,
                'size': size
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取虚拟客服列表失败: {str(e)}",
                data=None
            )

    def update_virtual_customer_service(self, cs_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新虚拟客服信息"""
        try:
            from shared.models.virtual_customer_service import VirtualCustomerService

            # 查找虚拟客服
            cs = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.id == cs_id,
                VirtualCustomerService.is_deleted == False
            ).first()

            if not cs:
                raise BusinessException(
                    code=404,
                    message="未找到该虚拟客服",
                    data=None
                )

            # 更新允许的字段
            allowed_fields = ['name', 'status']
            updated_fields = []

            for field in allowed_fields:
                if field in update_data and update_data[field] is not None:
                    setattr(cs, field, update_data[field])
                    updated_fields.append(field)

            if updated_fields:
                self.db.commit()

            return {
                'id': cs.id,
                'name': cs.name,
                'account': cs.account,
                'status': cs.status,
                'updated_fields': updated_fields
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"更新虚拟客服失败: {str(e)}",
                data=None
            )

    def delete_virtual_customer_service(self, cs_id: int) -> Dict[str, Any]:
        """删除虚拟客服（软删除）"""
        try:
            from shared.models.virtual_customer_service import VirtualCustomerService

            # 查找虚拟客服
            cs = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.id == cs_id,
                VirtualCustomerService.is_deleted == False
            ).first()

            if not cs:
                raise BusinessException(
                    code=404,
                    message="未找到该虚拟客服",
                    data=None
                )

            # 软删除虚拟客服记录
            cs.is_deleted = True

            # 软删除关联的用户账号
            user = self.db.query(OriginalUser).filter(
                OriginalUser.id == cs.user_id
            ).first()

            if user:
                user.isDeleted = True

            self.db.commit()

            return {
                'id': cs.id,
                'name': cs.name,
                'account': cs.account,
                'deleted': True
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"删除虚拟客服失败: {str(e)}",
                data=None
            )

    def export_student_income_data(self, start_date: str = None, end_date: str = None,
                                 student_ids: List[int] = None) -> bytes:
        """
        导出学生收入数据为Excel

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            student_ids: 指定学生ID列表

        Returns:
            bytes: Excel文件内容
        """
        try:
            from sqlalchemy import and_, func
            from sqlalchemy.sql import case
            from shared.models.tasks import Tasks
            from shared.models.userinfo import UserInfo
            from shared.models.original_user import OriginalUser
            import pandas as pd
            import io

            # 查询所有学生
            students_query = self.db.query(UserInfo).filter(
                UserInfo.level == '3',  # 学员级别
                UserInfo.isDeleted == False
            )

            # 添加学生ID过滤
            if student_ids:
                students_query = students_query.filter(UserInfo.roleId.in_(student_ids))

            students = students_query.all()

            # 创建结果列表
            results = []
            for student in students:
                # 查询该学生的任务统计（只查询真实任务，不包括虚拟任务）
                task_conditions = [
                    Tasks.is_virtual.is_(False),  # 只查询真实任务
                    Tasks.accepted_by.like(f'%{student.roleId}%')  # 该学生接取的任务
                ]

                # 添加日期过滤
                if start_date:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                    task_conditions.append(Tasks.created_at >= start_datetime)
                if end_date:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                    task_conditions.append(Tasks.created_at <= end_datetime)

                # 统计该学生的任务数据
                task_stats = self.db.query(
                    func.count(Tasks.id).label('total_tasks'),
                    func.sum(Tasks.commission).label('total_income'),
                    func.count(
                        case((Tasks.status == '已完成', 1))
                    ).label('completed_tasks'),
                    func.sum(
                        case((Tasks.status == '已完成', Tasks.commission), else_=0)
                    ).label('completed_income')
                ).filter(and_(*task_conditions)).first()

                # 为每个学生创建一个记录
                class StudentResult:
                    def __init__(self, student_id, student_name, phone_number, id_card,
                               total_tasks, total_income, completed_tasks, completed_income):
                        self.student_id = student_id
                        self.student_name = student_name
                        self.phone_number = phone_number
                        self.id_card = id_card
                        self.total_tasks = total_tasks
                        self.total_income = total_income
                        self.completed_tasks = completed_tasks
                        self.completed_income = completed_income

                result = StudentResult(
                    student_id=student.roleId,
                    student_name=student.name or '',
                    phone_number=student.phone_number or '',
                    id_card='',  # 不显示身份证
                    total_tasks=task_stats.total_tasks or 0,
                    total_income=float(task_stats.total_income or 0),
                    completed_tasks=task_stats.completed_tasks or 0,
                    completed_income=float(task_stats.completed_income or 0)
                )
                results.append(result)

            # 转换为DataFrame
            data = []
            for row in results:
                data.append({
                    '学生ID': row.student_id,
                    '学生姓名': row.student_name or '',
                    '手机号': row.phone_number or '',
                    '总任务数': row.total_tasks or 0,
                    '总收入金额': float(row.total_income or 0),
                    '已完成任务数': row.completed_tasks or 0,
                    '已完成收入': float(row.completed_income or 0),
                    '完成率': round((row.completed_tasks or 0) / max(row.total_tasks or 1, 1) * 100, 2),
                    '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '补贴金额': 0  # 这一列供用户填写补贴金额
                })

            if not data:
                # 如果没有数据，创建一个示例行
                data.append({
                    '学生ID': '',
                    '学生姓名': '示例学生',
                    '手机号': '',
                    '总任务数': 0,
                    '总收入金额': 0.0,
                    '已完成任务数': 0,
                    '已完成收入': 0.0,
                    '完成率': 0.0,
                    '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '补贴金额': 200.0  # 示例补贴金额
                })

            df = pd.DataFrame(data)

            # 创建Excel文件
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 写入学生收入数据
                df.to_excel(writer, sheet_name='学生收入统计', index=False)

                # 获取工作表对象进行格式化
                worksheet = writer.sheets['学生收入统计']

                # 设置列宽
                column_widths = {
                    'A': 10,  # 学生ID
                    'B': 15,  # 学生姓名
                    'C': 15,  # 手机号
                    'D': 20,  # 身份证号
                    'E': 12,  # 总任务数
                    'F': 15,  # 总收入金额
                    'G': 15,  # 已完成任务数
                    'H': 15,  # 已完成收入
                    'I': 10,  # 完成率
                    'J': 20,  # 导出时间
                    'K': 15,  # 补贴金额
                }

                for col, width in column_widths.items():
                    worksheet.column_dimensions[col].width = width

                # 添加说明工作表
                instructions = pd.DataFrame([
                    ['说明', ''],
                    ['1. 学生收入统计', '显示学生的任务完成情况和收入统计'],
                    ['2. 补贴金额列', '请在此列填写要给学生的补贴金额'],
                    ['3. 导入流程', '填写补贴金额后，将此文件导入到虚拟订单系统'],
                    ['4. 注意事项', '补贴金额必须为正数，系统会自动生成5的倍数任务'],
                    ['', ''],
                    ['字段说明', ''],
                    ['学生ID', '系统内部学生唯一标识'],
                    ['学生姓名', '学生真实姓名'],
                    ['手机号', '学生联系电话'],
                    ['身份证号', '学生身份证号码'],
                    ['总任务数', '学生接取的所有任务数量'],
                    ['总收入金额', '学生所有任务的总金额'],
                    ['已完成任务数', '学生已完成的任务数量'],
                    ['已完成收入', '学生已完成任务的收入金额'],
                    ['完成率', '任务完成率百分比'],
                    ['导出时间', '数据导出的时间'],
                    ['补贴金额', '要给学生的补贴金额（请填写）']
                ], columns=['项目', '说明'])

                instructions.to_excel(writer, sheet_name='使用说明', index=False)

                # 设置说明工作表的列宽
                instructions_sheet = writer.sheets['使用说明']
                instructions_sheet.column_dimensions['A'].width = 20
                instructions_sheet.column_dimensions['B'].width = 50

            output.seek(0)
            return output.getvalue()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"导出学生收入数据失败的详细错误: {error_details}")
            raise BusinessException(
                code=500,
                message=f"导出学生收入数据失败: {str(e)}",
                data=None
            )

    def get_student_income_summary(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        获取学生收入汇总统计

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict: 汇总统计数据
        """
        try:
            from sqlalchemy import and_, func
            from sqlalchemy.sql import case
            from shared.models.tasks import Tasks
            from shared.models.userinfo import UserInfo
            from shared.models.virtual_order_pool import VirtualOrderPool

            # 基础查询 - 统计学生数量
            query = self.db.query(UserInfo).filter(
                UserInfo.level == '3',  # 学员级别
                UserInfo.isDeleted == False
            )

            total_students = query.count()

            # 从补贴池统计总补贴金额
            pool_stats = self.db.query(
                func.sum(VirtualOrderPool.total_subsidy).label('total_subsidy'),
                func.sum(VirtualOrderPool.completed_amount).label('total_completed')
            ).first()

            # 任务统计查询 (status=4表示已完成)
            task_query = self.db.query(
                func.count(Tasks.id).label('total_tasks'),
                func.count(
                    case((Tasks.status == '4', 1))
                ).label('completed_tasks')
            ).filter(Tasks.is_virtual.is_(True))  # 只统计虚拟任务

            # 添加日期过滤
            if start_date:
                task_query = task_query.filter(Tasks.created_at >= start_date)
            if end_date:
                task_query = task_query.filter(Tasks.created_at <= end_date)

            task_stats = task_query.first()

            # 使用补贴池的数据作为总金额和已完成金额
            total_amount = float(pool_stats.total_subsidy or 0)
            completed_amount = float(pool_stats.total_completed or 0)

            return {
                'total_students': total_students,
                'total_tasks': task_stats.total_tasks or 0,
                'total_amount': total_amount,  # 使用补贴池的总补贴金额
                'completed_tasks': task_stats.completed_tasks or 0,
                'completed_amount': completed_amount,  # 使用补贴池的已完成金额
                'completion_rate': round(
                    (task_stats.completed_tasks or 0) / max(task_stats.total_tasks or 1, 1) * 100, 2
                ),
                'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取学生收入汇总失败: {str(e)}",
                data=None
            )



    def get_student_income_stats(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        获取学生收入统计信息

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            Dict: 统计信息
        """
        try:
            from sqlalchemy import and_, func
            from shared.models.tasks import Tasks

            # 构建查询条件
            query_conditions = [
                Tasks.is_virtual.is_(False),  # 只查询真实任务
                Tasks.status == '已完成',   # 只查询已完成的任务
                Tasks.accepted_by.isnot(None)  # 有接取人的任务
            ]

            # 添加日期过滤
            if start_date:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query_conditions.append(Tasks.created_at >= start_datetime)

            if end_date:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                query_conditions.append(Tasks.created_at <= end_datetime)

            # 统计查询
            total_tasks = self.db.query(Tasks).filter(and_(*query_conditions)).count()
            total_income = self.db.query(func.sum(Tasks.commission)).filter(and_(*query_conditions)).scalar() or 0

            # 统计学生数量（去重）
            student_count_query = self.db.query(Tasks.accepted_by).filter(and_(*query_conditions)).distinct()
            unique_students = set()
            for result in student_count_query:
                if result.accepted_by:
                    try:
                        student_id = int(result.accepted_by.split(',')[0]) if ',' in result.accepted_by else int(result.accepted_by)
                        unique_students.add(student_id)
                    except (ValueError, AttributeError):
                        continue

            return {
                'total_students': len(unique_students),
                'total_tasks': total_tasks,
                'total_income': float(total_income),
                'average_income_per_student': round(float(total_income) / len(unique_students), 2) if unique_students else 0,
                'average_income_per_task': round(float(total_income) / total_tasks, 2) if total_tasks > 0 else 0,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取学生收入统计失败: {str(e)}",
                data=None
            )

    def update_virtual_task_completion(self, task_id: int) -> Dict[str, Any]:
        """
        更新虚拟任务完成状态，同时更新学生补贴池的完成金额

        Args:
            task_id: 任务ID

        Returns:
            Dict: 更新结果
        """
        try:
            # 查找虚拟任务
            task = self.db.query(Tasks).filter(
                and_(
                    Tasks.id == task_id,
                    Tasks.is_virtual.is_(True)
                )
            ).first()

            if not task:
                raise BusinessException(
                    code=404,
                    message="未找到指定的虚拟任务",
                    data=None
                )

            # 检查任务状态是否为已完成
            if task.status != '4':
                raise BusinessException(
                    code=400,
                    message="任务状态不是已完成状态",
                    data=None
                )

            # 查找对应的学生补贴池
            pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == task.target_student_id
            ).first()

            if not pool:
                raise BusinessException(
                    code=404,
                    message="未找到对应的学生补贴池",
                    data=None
                )

            # 更新补贴池的完成金额
            pool.completed_amount += task.commission

            # 更新剩余金额：总补贴 - 已完成金额
            pool.remaining_amount = pool.total_subsidy - pool.completed_amount

            # 更新已分配金额：总补贴 - 剩余金额
            pool.allocated_amount = pool.total_subsidy - pool.remaining_amount

            # 确保剩余金额不为负数
            if pool.remaining_amount < 0:
                pool.remaining_amount = Decimal('0')
                pool.allocated_amount = pool.total_subsidy

            pool.updated_at = datetime.now()

            self.db.commit()

            return {
                'task_id': task_id,
                'student_id': task.target_student_id,
                'student_name': pool.student_name,
                'task_commission': float(task.commission),
                'total_completed_amount': float(pool.completed_amount),
                'updated_at': pool.updated_at
            }

        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"更新虚拟任务完成状态失败: {str(e)}",
                data=None
            )

    def sync_completed_virtual_tasks(self) -> Dict[str, Any]:
        """
        同步所有已完成的虚拟任务到学生补贴池
        用于修复历史数据或手动同步

        Returns:
            Dict: 同步结果统计
        """
        try:
            # 查找所有已完成但未同步的虚拟任务
            completed_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.status == '4',
                    Tasks.target_student_id.isnot(None)
                )
            ).all()

            if not completed_tasks:
                return {
                    'synced_tasks': 0,
                    'affected_students': 0,
                    'total_amount': 0.0,
                    'message': '没有需要同步的已完成虚拟任务'
                }

            # 按学生分组统计
            student_tasks = {}
            for task in completed_tasks:
                student_id = task.target_student_id
                if student_id not in student_tasks:
                    student_tasks[student_id] = []
                student_tasks[student_id].append(task)

            synced_count = 0
            total_amount = Decimal('0')
            affected_students = 0

            for student_id, tasks in student_tasks.items():
                # 获取学生补贴池
                pool = self.db.query(VirtualOrderPool).filter(
                    VirtualOrderPool.student_id == student_id
                ).first()

                if not pool:
                    continue

                # 计算该学生已完成任务的总金额
                student_completed_amount = sum(task.commission for task in tasks)

                # 重置并更新完成金额（避免重复计算）
                pool.completed_amount = student_completed_amount

                # 更新剩余金额：总补贴 - 已完成金额
                pool.remaining_amount = pool.total_subsidy - pool.completed_amount

                # 更新已分配金额：总补贴 - 剩余金额
                pool.allocated_amount = pool.total_subsidy - pool.remaining_amount

                # 确保剩余金额不为负数
                if pool.remaining_amount < 0:
                    pool.remaining_amount = Decimal('0')
                    pool.allocated_amount = pool.total_subsidy

                pool.updated_at = datetime.now()

                synced_count += len(tasks)
                total_amount += student_completed_amount
                affected_students += 1

            self.db.commit()

            return {
                'synced_tasks': synced_count,
                'affected_students': affected_students,
                'total_amount': float(total_amount),
                'message': f'成功同步 {synced_count} 个已完成任务，影响 {affected_students} 个学生'
            }

        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"同步已完成虚拟任务失败: {str(e)}",
                data=None
            )
