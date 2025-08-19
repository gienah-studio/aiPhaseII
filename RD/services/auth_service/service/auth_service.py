from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
import bcrypt
from decimal import Decimal

from shared.config import settings
from shared.models.user import User
from shared.models.original_user import OriginalUser
from shared.models.agents import Agents
from shared.models.userinfo import UserInfo
from shared.models.tasks import Tasks
from shared.utils.security import create_access_token
from shared.exceptions import BusinessException
from shared.utils.redis_util import RedisUtil


class AuthService:
    def __init__(self, db: Session):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.salt_rounds = 10  # bcrypt盐轮数

        # 注：在认证模板中，我们移除了OSS文件上传功能
        # 实际项目中可以根据需要添加文件上传功能

        # 初始化RedisUtil
        self.redis_util = RedisUtil()

    def hash_password(self, password: str) -> str:
        """生成哈希密码（加盐加密）"""
        salt = bcrypt.gensalt(rounds=self.salt_rounds)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def compare_password(self, password: str, hash_password: str) -> bool:
        """验证密码（比较输入的密码和哈希密码）"""
        return bcrypt.checkpw(password.encode('utf-8'), hash_password.encode('utf-8'))



    def login(self, username: str, password: str, client_ip: str = None):
        """账号密码登录（参考NestJS逻辑）"""
        # 查找用户
        user = self.db.query(OriginalUser).filter(
            OriginalUser.username == username,
            OriginalUser.isDeleted == False
        ).first()

        if not user:
            raise BusinessException(
                code=400,
                message="账号或密码不正确",
                data=None
            )

        # 验证密码
        if not self.compare_password(password, user.password):
            raise BusinessException(
                code=400,
                message="账号或密码不正确",
                data=None
            )

        # 查询用户记录，排除已删除的用户
        # admin 和虚拟客服可以直接登录，其他用户需要检查 userinfo 表
        if username != 'admin' and user.role != 'virtual_customer_service':
            user_record = self.db.query(UserInfo).filter(
                UserInfo.account == username,
                UserInfo.isDeleted == False
            ).first()

            if not user_record:
                raise BusinessException(
                    code=404,
                    message="用户不存在或已被删除",
                    data=None
                )

            # 根据 agentId 查询 Agents 表中的 status 值
            agent_record = self.db.query(Agents).filter(Agents.id == user_record.agentId).first()
            if not agent_record:
                raise BusinessException(
                    code=404,
                    message="未找到当前用户的代理信息",
                    data=None
                )

            agent_status = agent_record.status

            # 根据 agentStatus 判断处理逻辑
            if agent_status == '0':
                raise BusinessException(
                    code=400,
                    message="当前用户正在审批",
                    data=None
                )
            elif agent_status == '2':
                raise BusinessException(
                    code=404,
                    message="未找到当前用户",
                    data=None
                )

        # 获取上次登录时间
        last_login_time = None
        if user.lastLoginTime:
            last_login_time = user.lastLoginTime.strftime('%Y-%m-%d %H:%M:%S')

        # 更新最后登录时间
        user.lastLoginTime = datetime.now()
        self.db.commit()

        # 生成访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        # 处理用户类型，虚拟客服和admin使用特殊的数字标识
        user_type = 0  # 默认值
        if user.role == 'admin':
            user_type = 0
        elif user.role == '5':  # 虚拟客服角色为5
            user_type = 6  # 虚拟客服使用6作为用户类型
        else:
            # 其他角色尝试转换为整数
            try:
                user_type = int(user.role)
            except (ValueError, TypeError):
                user_type = 0

        access_token = create_access_token(
            data={
                "user_id": user.id,
                "account": user.username,
                "user_type": user_type,
                "sub": str(user.id),  # JWT标准要求sub字段必须是字符串
                "username": user.username,  # 保持向后兼容
                "role": user.role  # 保持向后兼容
            },
            expires_delta=access_token_expires
        )

        # 记录登录日志
        if client_ip:
            self.log_user_login(user.id, client_ip)

        return {
            "access_token": access_token,
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "last_login_time": last_login_time
        }

    def reset_password(self, user_id: int) -> bool:
        """重置密码（参考NestJS逻辑）"""
        try:
            # 1. 直接通过userId在user表中查找用户
            user = self.db.query(OriginalUser).filter(OriginalUser.id == user_id).first()
            if not user:
                raise BusinessException(
                    code=404,
                    message="用户不存在",
                    data=None
                )

            # 2. 检查用户是否为管理员，管理员不能重置密码
            if user.username == 'admin':
                raise BusinessException(
                    code=400,
                    message="不能重置管理员密码",
                    data=None
                )

            # 3. 将密码重置为123456并加密
            new_password = '123456'
            hashed_password = self.hash_password(new_password)

            # 4. 更新用户表中的密码
            user.password = hashed_password
            self.db.commit()

            # 5. 同时更新userinfo表中的initial_password字段
            user_info = self.db.query(UserInfo).filter(UserInfo.account == user.username).first()
            if user_info:
                user_info.initial_password = hashed_password
                self.db.commit()

            return True
        except BusinessException as e:
            raise e
        except Exception as e:
            print(f"Reset password error: {str(e)}")
            raise BusinessException(
                code=500,
                message="重置密码失败",
                data=None
            )

    def change_password(self, user_id: int, old_password: str, new_password: str, confirm_password: str) -> bool:
        """修改密码（参考NestJS逻辑）"""
        try:
            # 1. 验证新密码和确认密码是否一致
            if new_password != confirm_password:
                raise BusinessException(
                    code=400,
                    message="新密码和确认密码不一致",
                    data=None
                )

            # 2. 从数据库中查找用户
            user = self.db.query(OriginalUser).filter(OriginalUser.id == user_id).first()
            if not user:
                raise BusinessException(
                    code=404,
                    message="用户不存在",
                    data=None
                )

            # 3. 验证原密码是否正确
            if not self.compare_password(old_password, user.password):
                raise BusinessException(
                    code=400,
                    message="原密码错误",
                    data=None
                )

            # 4. 检查新密码是否与原密码相同
            if self.compare_password(new_password, user.password):
                raise BusinessException(
                    code=400,
                    message="新密码不能与原密码相同",
                    data=None
                )

            # 5. 加密新密码
            hashed_new_password = self.hash_password(new_password)

            # 6. 更新用户表中的密码
            user.password = hashed_new_password
            self.db.commit()

            # 7. 同时更新userinfo表中的initial_password字段
            user_info = self.db.query(UserInfo).filter(UserInfo.account == user.username).first()
            if user_info:
                user_info.initial_password = hashed_new_password
                self.db.commit()

            return True
        except BusinessException as e:
            raise e
        except Exception as e:
            print(f"Change password error: {str(e)}")
            raise BusinessException(
                code=500,
                message="修改密码失败",
                data=None
            )






    def get_user_profile(self, user_id: int):
        """获取用户信息（简化版本，适用于认证模板）"""
        try:
            # 查询用户
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise BusinessException(
                    code=400,
                    message="用户不存在",
                    data=None
                )

            # 确保 create_time 和 update_time 字段有值
            create_time = user.create_time
            update_time = user.update_time

            if create_time is None:
                create_time = datetime.now()
            if update_time is None:
                update_time = datetime.now()

            # 构建简化的用户响应数据（适用于认证模板）
            return {
                "id": user.id,
                "enterprise_id": user.enterprise_id,
                "account": user.account,
                "name": user.name,
                "phone": user.phone,
                "email": user.email,
                "avatar": user.avatar,
                "role": user.role.value,
                "status": user.status.value,
                "remark": user.remark,
                "create_time": create_time,
                "update_time": update_time,
                "permissions": [],  # 简化版本，不包含复杂权限
                "roles": []  # 简化版本，不包含角色
            }

        except BusinessException as e:
            raise e
        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取用户信息失败: {str(e)}",
                data=None
            )





    def log_user_login(self, user_id: int, ip: str):
        """记录登录日志"""
        try:
            login_log = {
                "user_id": user_id,
                "login_time": datetime.now(),
                "ip": ip
            }
            self.db.execute(
                text("""
                INSERT INTO login_log (user_id, login_time, ip)
                VALUES (:user_id, :login_time, :ip)
                """),
                login_log
            )
            self.db.commit()
        except Exception as e:
            print(f"写入登录日志失败: {str(e)}")
            # 不影响主流程





    def logout(self, user_id: int, token: str):
        """退出登录，使当前token失效"""
        # 将token加入黑名单，有效期设置为token的剩余有效期
        try:
            # 默认先设置一个较长的过期时间，确保token失效
            expiration = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 转换为秒
            RedisUtil.add_token_to_blacklist(token, expiration)
            return True
        except Exception as e:
            print(f"退出登录时出错: {str(e)}")
            # 即使失败也返回成功，不影响用户体验
            return True

    def get_user_info(self, user_id: int):
        """获取用户详细信息（简化版本，适用于认证模板）"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise BusinessException(
                code=404,
                message="用户不存在",
                data=None
            )

        # 确保 create_time 和 update_time 字段有值
        create_time = user.create_time
        update_time = user.update_time

        if create_time is None:
            create_time = datetime.now()
        if update_time is None:
            update_time = datetime.now()

        return {
            "id": user.id,
            "enterprise_id": user.enterprise_id,
            "account": user.account,
            "name": user.name,
            "phone": user.phone,
            "email": user.email,
            "avatar": user.avatar,
            "role": user.role.value,
            "status": user.status.value,
            "remark": user.remark,
            "create_time": create_time,
            "update_time": update_time
        }

    def update_user_info(self, user_id: int, user_data: dict):
        """更新用户信息"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise BusinessException(
                code=404,
                message="用户不存在",
                data=None
            )

        # 更新基本信息
        if "name" in user_data and user_data["name"]:
            user.name = user_data["name"]

        # 更新邮箱（如果提供了）
        if "email" in user_data and user_data["email"]:
            # 检查邮箱是否已存在
            existing_email = self.db.query(User).filter(
                User.email == user_data["email"],
                User.id != user_id
            ).first()
            if existing_email:
                raise BusinessException(
                    code=400,
                    message="邮箱已被其他用户使用",
                    data=None
                )
            user.email = user_data["email"]

        # 更新头像（如果提供了）
        if "avatar" in user_data and user_data["avatar"]:
            user.avatar = user_data["avatar"]

        # 确保 update_time 字段被更新
        user.update_time = datetime.now()

        # 保存更改
        self.db.commit()

        # 获取更新后的用户信息
        user_info = self.get_user_info(user_id)

        # 确保必要的字段存在
        if user_info.get("create_time") is None:
            user_info["create_time"] = user.create_time or datetime.now()
        if user_info.get("update_time") is None:
            user_info["update_time"] = user.update_time or datetime.now()

        return user_info

    def get_all_students_income_stats(self, page: int = 1, size: int = 10) -> dict:
        """获取所有学员收入统计列表

        Returns:
            dict: 所有学员收入统计数据
        """
        try:
            print("[DEBUG] 开始获取所有学员收入统计...")

            # 1. 获取所有学员信息
            students = self.db.query(UserInfo).filter(
                UserInfo.level == '3',  # 学员级别
                UserInfo.isDeleted == False
            ).all()

            print(f"[DEBUG] 找到 {len(students)} 个学员")

            if not students:
                print("[DEBUG] 没有找到学员，返回空列表")
                return {
                    "students": [],
                    "total": 0,
                    "stat_date": (datetime.now().date() - timedelta(days=1)).strftime('%Y-%m-%d')
                }

            # 2. 计算前一天的日期范围
            yesterday = datetime.now().date() - timedelta(days=1)
            start_time = datetime.combine(yesterday, datetime.min.time())
            end_time = datetime.combine(yesterday, datetime.max.time())

            # 3. 查询前一天完成的任务
            completed_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.status == '4',  # 任务状态为已完成
                    Tasks.created_at >= start_time,
                    Tasks.created_at <= end_time
                )
            ).all()

            # 4. 为每个学员计算收入统计
            students_stats = []

            for i, student in enumerate(students):
                print(f"[DEBUG] 处理学员 {i+1}/{len(students)}: {student.name} (ID: {student.roleId})")

                # 获取学员的代理信息
                agent_record = self.db.query(Agents).filter(
                    Agents.id == student.agentId
                ).first()

                agent_rebate = "0.00"
                if agent_record and agent_record.agent_rebate:
                    # 处理百分比格式，如 "15%" -> "0.15" 或 "60" -> "0.60"
                    rebate_str = agent_record.agent_rebate.replace('%', '') if '%' in agent_record.agent_rebate else agent_record.agent_rebate
                    rebate_value = float(rebate_str)
                    # 如果值大于1，说明是百分比形式（如60），需要除以100
                    if rebate_value > 1:
                        agent_rebate = str(rebate_value / 100)
                    else:
                        agent_rebate = str(rebate_value)

                print(f"[DEBUG] 学员 {student.name} 的代理返佣比例: {agent_rebate}")

                # 计算该学员的收入统计
                total_commission = Decimal('0.00')
                completed_orders = 0
                agent_rebate_decimal = Decimal(agent_rebate) if agent_rebate else Decimal('0.00')
                original_commission = Decimal('0.00')

                for task in completed_tasks:
                    is_student_task = False
                    
                    # 判断任务是否属于该学生
                    if hasattr(task, 'is_virtual') and task.is_virtual:
                        # 虚拟任务：通过target_student_id判断
                        if hasattr(task, 'target_student_id') and task.target_student_id == student.roleId:
                            is_student_task = True
                            print(f"[DEBUG] 虚拟任务 {task.id} 属于学生 {student.roleId} (通过target_student_id)")
                    else:
                        # 普通任务：通过accepted_by判断
                        if task.accepted_by:
                            accepted_user_ids = task.accepted_by.split(',')
                            if str(student.roleId) in accepted_user_ids:
                                is_student_task = True
                                print(f"[DEBUG] 普通任务 {task.id} 属于学生 {student.roleId} (通过accepted_by)")
                    
                    if is_student_task and task.commission:
                        commission = Decimal(str(task.commission))
                        original_commission += commission

                        # 虚拟任务和普通任务都按代理返佣比例计算实际收入
                        actual_commission = commission * agent_rebate_decimal

                        if hasattr(task, 'is_virtual') and task.is_virtual:
                            print(f"[DEBUG] 虚拟任务 {task.id}: 佣金 {commission}, 返佣比例 {agent_rebate_decimal}, 实际收入 {actual_commission}")
                        else:
                            print(f"[DEBUG] 普通任务 {task.id}: 佣金 {commission}, 返佣比例 {agent_rebate_decimal}, 实际收入 {actual_commission}")

                        total_commission += actual_commission
                        completed_orders += 1

                # 计算虚拟任务和普通任务的统计
                virtual_commission = Decimal('0.00')
                normal_commission = Decimal('0.00')
                virtual_orders = 0
                normal_orders = 0

                for task in completed_tasks:
                    is_student_task = False
                    
                    # 判断任务是否属于该学生
                    if hasattr(task, 'is_virtual') and task.is_virtual:
                        # 虚拟任务：通过target_student_id判断
                        if hasattr(task, 'target_student_id') and task.target_student_id == student.roleId:
                            is_student_task = True
                    else:
                        # 普通任务：通过accepted_by判断
                        if task.accepted_by:
                            accepted_user_ids = task.accepted_by.split(',')
                            if str(student.roleId) in accepted_user_ids:
                                is_student_task = True
                    
                    if is_student_task and task.commission:
                        commission = Decimal(str(task.commission))
                        if hasattr(task, 'is_virtual') and task.is_virtual:
                            # 虚拟任务：按返佣比例计算
                            virtual_commission += commission * agent_rebate_decimal
                            virtual_orders += 1
                        else:
                            # 普通任务：按返佣比例计算
                            normal_commission += commission * agent_rebate_decimal
                            normal_orders += 1

                # 添加学员统计数据（使用驼峰命名，会被中间件转换）
                student_stat = {
                    "student_id": student.roleId,
                    "student_name": student.name or "",
                    "yesterday_income": str(original_commission),  # 原始佣金总额
                    "yesterday_completed_orders": completed_orders,
                    "commission_rate": agent_rebate if completed_orders > 0 else "N/A",  # 有任务时显示返佣比例
                    "actual_income": str(total_commission),  # 实际到手金额
                    "phone_number": student.phone_number or "",
                    "virtual_orders": virtual_orders,  # 虚拟任务数量
                    "normal_orders": normal_orders,  # 普通任务数量
                    "virtual_commission": str(virtual_commission),  # 虚拟任务佣金
                    "normal_commission": str(normal_commission)  # 普通任务佣金
                    # 移除 agent_id 字段
                }
                students_stats.append(student_stat)

            # 按完成订单数从大到小排序
            students_stats.sort(key=lambda x: x["yesterday_completed_orders"], reverse=True)

            # 计算分页
            total_students = len(students_stats)
            start_index = (page - 1) * size
            end_index = start_index + size
            paginated_students = students_stats[start_index:end_index]

            result = {
                "students": paginated_students,
                "total": total_students,
                "page": page,
                "size": size,
                "total_pages": (total_students + size - 1) // size,  # 向上取整
                "stat_date": yesterday.strftime('%Y-%m-%d')
            }

            print(f"[DEBUG] 返回结果: 第{page}页，共 {len(paginated_students)} 个学员，总计 {total_students} 个学员")
            return result

        except BusinessException as e:
            raise e
        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取学员收入统计失败: {str(e)}",
                data=None
            )


