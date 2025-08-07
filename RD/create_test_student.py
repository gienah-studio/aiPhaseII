#!/usr/bin/env python3
"""
创建测试学员数据
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.database.session import SessionLocal
from shared.models.original_user import OriginalUser
from shared.models.userinfo import UserInfo
from shared.models.agents import Agents
from shared.models.tasks import Tasks
import bcrypt

def create_test_student():
    """创建测试学员数据"""
    db = SessionLocal()
    
    try:
        print("🚀 开始创建测试学员数据...")
        
        # 1. 创建测试代理（如果不存在）
        agent = db.query(Agents).filter(Agents.id == 999).first()
        if not agent:
            agent = Agents(
                id=999,
                agent_rebate="0.10",
                student_commission="0.15",  # 学员分佣比例15%
                rebate="0.05",
                status="1",  # 正常状态
                approvalsNumber=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                direct_students_count=1,
                is_read=0,
                isDeleted=False
            )
            db.add(agent)
            db.flush()
            print(f"✅ 创建测试代理，ID: {agent.id}")
        else:
            print(f"✅ 测试代理已存在，ID: {agent.id}")
        
        # 2. 创建测试用户账号（如果不存在）
        test_username = "test_student"
        user = db.query(OriginalUser).filter(
            OriginalUser.username == test_username,
            OriginalUser.isDeleted == False
        ).first()
        
        if not user:
            # 生成密码哈希
            password = "password123"
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            
            user = OriginalUser(
                username=test_username,
                password=hashed_password,
                role="3",  # 学员角色
                lastLoginTime=None,
                isDeleted=False
            )
            db.add(user)
            db.flush()
            print(f"✅ 创建测试用户，ID: {user.id}, 用户名: {test_username}")
        else:
            print(f"✅ 测试用户已存在，ID: {user.id}, 用户名: {test_username}")
        
        # 3. 创建用户信息（如果不存在）
        user_info = db.query(UserInfo).filter(
            UserInfo.account == test_username,
            UserInfo.isDeleted == False
        ).first()
        
        if not user_info:
            user_info = UserInfo(
                userId=user.id,
                studentId=None,
                name="测试学员",
                id_card="123456789012345678",
                phone_number="13800138000",
                bank_card="6222000000000000000",
                account=test_username,
                initial_password="password123",
                avatar_url=None,
                agentId=agent.id,
                level="3",  # 学员级别
                parentId=0,
                isDeleted=False,
                needsComputer="否"
            )
            db.add(user_info)
            db.flush()
            print(f"✅ 创建用户信息，roleId: {user_info.roleId}")
        else:
            print(f"✅ 用户信息已存在，roleId: {user_info.roleId}")
        
        # 4. 创建一些测试任务数据（前一天完成的任务）
        yesterday = datetime.now().date() - timedelta(days=1)
        start_time = datetime.combine(yesterday, datetime.min.time())
        end_time = datetime.combine(yesterday, datetime.max.time())
        
        # 检查是否已有测试任务
        existing_tasks = db.query(Tasks).filter(
            Tasks.accepted_by == str(user_info.roleId),
            Tasks.created_at >= start_time,
            Tasks.created_at <= end_time
        ).count()
        
        if existing_tasks == 0:
            # 创建几个测试任务
            test_tasks = [
                {
                    "summary": "测试任务1 - 数据处理",
                    "commission": Decimal("30.00"),
                    "payment_status": "4"  # 已结算
                },
                {
                    "summary": "测试任务2 - 内容整理", 
                    "commission": Decimal("25.00"),
                    "payment_status": "4"  # 已结算
                },
                {
                    "summary": "测试任务3 - 文档编辑",
                    "commission": Decimal("20.00"),
                    "payment_status": "4"  # 已结算
                }
            ]
            
            for i, task_data in enumerate(test_tasks):
                task = Tasks(
                    summary=task_data["summary"],
                    requirement="测试任务需求描述",
                    reference_images="",
                    source="测试来源",
                    order_number=f"TEST{yesterday.strftime('%Y%m%d')}{i+1:03d}",
                    commission=task_data["commission"],
                    commission_unit="人民币",
                    end_date=end_time,
                    delivery_date=end_time,
                    status="4",  # 已完成
                    task_style="数据处理",
                    task_type="测试任务",
                    created_at=start_time + timedelta(hours=i),
                    updated_at=end_time,
                    orders_number=1,
                    order_received_number=1,
                    founder="测试系统",
                    founder_id=0,
                    message="",
                    task_level="D",
                    accepted_by=str(user_info.roleId),
                    payment_status=task_data["payment_status"],
                    accepted_name=user_info.name,
                    is_renew="0",
                    is_virtual=False
                )
                db.add(task)
            
            print(f"✅ 创建了 {len(test_tasks)} 个测试任务")
        else:
            print(f"✅ 已存在 {existing_tasks} 个测试任务")
        
        # 提交所有更改
        db.commit()
        
        print("\n🎉 测试学员数据创建完成！")
        print(f"📋 测试信息:")
        print(f"   用户名: {test_username}")
        print(f"   密码: password123")
        print(f"   学员ID: {user_info.roleId}")
        print(f"   学员姓名: {user_info.name}")
        print(f"   代理ID: {agent.id}")
        print(f"   分佣比例: {agent.student_commission}")
        
        # 计算预期收入
        total_commission = sum(Decimal("30.00"), Decimal("25.00"), Decimal("20.00"))
        commission_rate = Decimal(agent.student_commission)
        actual_income = total_commission * (Decimal("1.00") - commission_rate)
        
        print(f"\n💰 预期统计结果:")
        print(f"   昨日总收入: ¥{total_commission}")
        print(f"   完成订单数: 3")
        print(f"   分佣比例: {agent.student_commission}")
        print(f"   实际到手: ¥{actual_income}")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建测试数据失败: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = create_test_student()
    if success:
        print("\n✅ 现在可以运行 test_student_income_api.py 来测试接口了")
    else:
        print("\n❌ 测试数据创建失败")
        sys.exit(1)
