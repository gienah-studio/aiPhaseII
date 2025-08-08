#!/usr/bin/env python3
"""
测试虚拟任务生成逻辑的修改
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from services.virtual_order_service.service.virtual_order_service import VirtualOrderService
from shared.database import SessionLocal

def test_amount_calculation():
    """测试金额计算逻辑"""
    print("=== 测试金额计算逻辑 ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    # 测试不同的总金额
    test_amounts = [Decimal('30'), Decimal('50'), Decimal('100'), Decimal('200')]
    
    for total_amount in test_amounts:
        amounts = service.calculate_task_amounts(total_amount)
        print(f"\n总金额: {total_amount}")
        print(f"分配结果: {amounts}")
        print(f"任务数量: {len(amounts)}")
        print(f"金额总和: {sum(amounts)}")
        
        # 验证每个金额都在5-25范围内
        for amount in amounts:
            if amount not in [Decimal('5'), Decimal('10'), Decimal('15'), Decimal('20'), Decimal('25')]:
                if amount <= Decimal('5'):  # 允许小于5的剩余金额
                    print(f"  ✓ 剩余金额: {amount}")
                else:
                    print(f"  ❌ 金额超出范围: {amount}")
            else:
                print(f"  ✓ 有效金额: {amount}")
    
    db.close()

def test_task_content_generation():
    """测试任务内容生成"""
    print("\n=== 测试任务内容生成 ===")

    db = SessionLocal()
    service = VirtualOrderService(db)

    print("生成20个随机任务内容（包含简单组合和智能模板）:")
    for i in range(20):
        content = service.generate_random_task_content()
        print(f"{i+1}. 标题: {content['summary']}")
        print(f"   描述: {content['requirement']}")
        print("-" * 80)

    db.close()

def test_virtual_task_creation():
    """测试虚拟任务创建"""
    print("\n=== 测试虚拟任务创建 ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    # 创建一个测试任务
    student_id = 999
    student_name = "测试学生"
    amount = Decimal('15')
    
    task = service.create_virtual_task(student_id, student_name, amount)
    
    print(f"任务标题: {task.summary}")
    print(f"任务描述: {task.requirement}")
    print(f"任务金额: {task.commission}")
    print(f"任务类别: {task.task_style}")
    print(f"创建时间: {task.created_at}")
    print(f"截止时间: {task.end_date}")
    print(f"交稿时间: {task.delivery_date}")
    print(f"目标学生ID: {task.target_student_id}")

    # 验证3小时生存周期
    end_time_diff = task.end_date - task.created_at
    end_hours_diff = end_time_diff.total_seconds() / 3600
    print(f"接单截止周期: {end_hours_diff} 小时")

    delivery_time_diff = task.delivery_date - task.created_at
    delivery_hours_diff = delivery_time_diff.total_seconds() / 3600
    print(f"交稿时间周期: {delivery_hours_diff} 小时")

    if abs(end_hours_diff - 3) < 0.1:  # 允许小的误差
        print("✓ 接单截止时间设置正确")
    else:
        print("❌ 接单截止时间设置错误")

    if abs(delivery_hours_diff - 3) < 0.1:  # 允许小的误差
        print("✓ 交稿时间设置正确")
    else:
        print("❌ 交稿时间设置错误")
    
    db.close()

if __name__ == "__main__":
    print("🚀 开始测试虚拟任务生成逻辑修改")
    print("=" * 50)
    
    try:
        test_amount_calculation()
        test_task_content_generation()
        test_virtual_task_creation()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
