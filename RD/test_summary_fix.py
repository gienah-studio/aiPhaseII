#!/usr/bin/env python3
"""
测试学生收入汇总修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_summary_fix():
    """测试汇总接口修复"""
    try:
        from services.virtual_order_service.service.virtual_order_service import VirtualOrderService
        from shared.database.session import get_db
        from shared.models.tasks import Tasks
        from sqlalchemy import func
        
        db = next(get_db())
        service = VirtualOrderService(db)
        
        print("=== 修复前后对比测试 ===")
        print()
        
        # 直接查询数据库验证
        print("1. 数据库直接查询结果:")
        
        # 虚拟任务统计
        virtual_stats = db.query(
            func.count(Tasks.id).label('total_tasks'),
            func.sum(Tasks.commission).label('total_amount'),
            func.count(Tasks.id).filter(Tasks.status == '4').label('completed_tasks'),
            func.sum(Tasks.commission).filter(Tasks.status == '4').label('completed_amount')
        ).filter(Tasks.is_virtual.is_(True)).first()
        
        print(f"   虚拟任务:")
        print(f"     总任务数: {virtual_stats.total_tasks or 0}")
        print(f"     总金额: {virtual_stats.total_amount or 0}")
        print(f"     已完成任务数: {virtual_stats.completed_tasks or 0}")
        print(f"     已完成金额: {virtual_stats.completed_amount or 0}")
        
        # 真实任务统计
        real_stats = db.query(
            func.count(Tasks.id).label('total_tasks'),
            func.sum(Tasks.commission).label('total_amount'),
            func.count(Tasks.id).filter(Tasks.status == '4').label('completed_tasks'),
            func.sum(Tasks.commission).filter(Tasks.status == '4').label('completed_amount')
        ).filter(Tasks.is_virtual.is_(False)).first()
        
        print(f"   真实任务:")
        print(f"     总任务数: {real_stats.total_tasks or 0}")
        print(f"     总金额: {real_stats.total_amount or 0}")
        print(f"     已完成任务数: {real_stats.completed_tasks or 0}")
        print(f"     已完成金额: {real_stats.completed_amount or 0}")
        
        print()
        
        # 测试修复后的汇总接口
        print("2. 修复后的汇总接口结果:")
        summary = service.get_student_income_summary()
        
        print(f"   学生总数: {summary['total_students']}")
        print(f"   任务总数: {summary['total_tasks']}")
        print(f"   总金额: {summary['total_amount']}")
        print(f"   已完成任务数: {summary['completed_tasks']}")
        print(f"   已完成金额: {summary['completed_amount']}")
        print(f"   完成率: {summary['completion_rate']}%")
        print(f"   统计时间: {summary['export_time']}")
        
        print()
        
        # 验证修复是否正确
        print("3. 修复验证:")
        if summary['total_amount'] == (virtual_stats.total_amount or 0):
            print("   ✅ 总金额现在正确统计虚拟任务")
        else:
            print("   ❌ 总金额统计仍有问题")
            
        if summary['total_tasks'] == (virtual_stats.total_tasks or 0):
            print("   ✅ 任务总数现在正确统计虚拟任务")
        else:
            print("   ❌ 任务总数统计仍有问题")
            
        if summary['completed_tasks'] == (virtual_stats.completed_tasks or 0):
            print("   ✅ 已完成任务数现在正确统计虚拟任务")
        else:
            print("   ❌ 已完成任务数统计仍有问题")
        
        print()
        print("修复说明:")
        print("- 修改了 get_student_income_summary 方法中的过滤条件")
        print("- 从 Tasks.is_virtual.is_(False) 改为 Tasks.is_virtual.is_(True)")
        print("- 现在只统计虚拟任务，符合虚拟订单系统的需求")
        
        db.close()
        
    except Exception as e:
        import traceback
        print(f"测试失败: {str(e)}")
        print(f"详细错误: {traceback.format_exc()}")

if __name__ == "__main__":
    test_summary_fix()
