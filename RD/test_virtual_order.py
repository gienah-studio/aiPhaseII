#!/usr/bin/env python3
"""
虚拟订单系统测试脚本
用于测试虚拟订单系统的基本功能
"""

import sys
import os
from decimal import Decimal
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.database.session import SessionLocal
from services.virtual_order_service.service.virtual_order_service import VirtualOrderService

def test_amount_calculation():
    """测试金额分配算法"""
    print("=== 测试金额分配算法 ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    test_amounts = [Decimal('200'), Decimal('150'), Decimal('203'), Decimal('5'), Decimal('13')]
    
    for amount in test_amounts:
        result = service.calculate_task_amounts(amount)
        total = sum(result)
        print(f"补贴金额: {amount} -> 分配结果: {result} -> 总和: {total}")
        assert total == amount, f"金额分配错误: {total} != {amount}"
    
    print("金额分配算法测试通过！\n")
    db.close()

def test_order_number_generation():
    """测试订单号生成"""
    print("=== 测试订单号生成 ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    # 生成10个订单号测试
    order_numbers = []
    for i in range(10):
        order_number = service.generate_order_number()
        order_numbers.append(order_number)
        print(f"订单号 {i+1}: {order_number}")
        
        # 验证订单号格式
        assert len(order_number) == 10, f"订单号长度错误: {len(order_number)}"
        assert all(c in '1234567890abcdef' for c in order_number), f"订单号包含非法字符: {order_number}"
    
    # 验证订单号唯一性
    assert len(set(order_numbers)) == len(order_numbers), "订单号存在重复"
    
    print("订单号生成测试通过！\n")
    db.close()

def test_virtual_task_creation():
    """测试虚拟任务创建"""
    print("=== 测试虚拟任务创建 ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    # 测试创建单个虚拟任务
    student_id = 1
    student_name = "测试学生"
    amount = Decimal('25')
    
    task = service.create_virtual_task(student_id, student_name, amount)
    
    print(f"创建的虚拟任务:")
    print(f"  订单号: {task.order_number}")
    print(f"  金额: {task.commission}")
    print(f"  是否虚拟任务: {task.is_virtual}")
    print(f"  任务简介: {task.summary}")
    print(f"  截止时间: {task.end_date}")
    print(f"  交稿时间: {task.delivery_date}")
    
    # 验证任务属性
    assert task.commission == amount, f"任务金额错误: {task.commission} != {amount}"
    assert task.is_virtual == True, "虚拟任务标识错误"
    assert task.order_number is not None, "订单号为空"
    assert len(task.order_number) == 10, f"订单号长度错误: {len(task.order_number)}"
    
    print("虚拟任务创建测试通过！\n")
    db.close()

def test_multiple_tasks_generation():
    """测试批量任务生成"""
    print("=== 测试批量任务生成 ===")

    db = SessionLocal()
    service = VirtualOrderService(db)

    student_id = 1
    student_name = "测试学生"
    subsidy_amount = Decimal('200')

    tasks = service.generate_virtual_tasks_for_student(student_id, student_name, subsidy_amount)

    print(f"为学生 {student_name} 生成了 {len(tasks)} 个虚拟任务:")
    total_amount = Decimal('0')
    for i, task in enumerate(tasks, 1):
        print(f"  任务 {i}: 订单号 {task.order_number}, 金额 {task.commission}")
        total_amount += task.commission

    print(f"任务总金额: {total_amount}")

    # 验证总金额
    assert total_amount == subsidy_amount, f"任务总金额错误: {total_amount} != {subsidy_amount}"

    # 验证所有任务都是虚拟任务
    for task in tasks:
        assert task.is_virtual == True, "存在非虚拟任务"
        assert task.commission >= 5 or task.commission == subsidy_amount, f"任务金额不符合规则: {task.commission}"

    print("批量任务生成测试通过！\n")
    db.close()

def test_virtual_customer_service_creation():
    """测试虚拟客服创建"""
    print("=== 测试虚拟客服创建 ===")

    db = SessionLocal()
    service = VirtualOrderService(db)

    # 测试创建虚拟客服
    cs_name = f"测试客服_{int(datetime.now().timestamp())}"
    cs_account = f"test_cs_{int(datetime.now().timestamp())}"
    cs_phone = "13800138000"
    cs_id_card = "123456789012345678"

    try:
        result = service.create_virtual_customer_service(
            name=cs_name,
            account=cs_account,
            phone_number=cs_phone,
            id_card=cs_id_card,
            initial_password="123456"
        )

        print(f"创建的虚拟客服:")
        print(f"  用户ID: {result['user_id']}")
        print(f"  角色ID: {result['role_id']}")
        print(f"  姓名: {result['name']}")
        print(f"  账号: {result['account']}")
        print(f"  级别: {result['level']}")
        print(f"  初始密码: {result['initial_password']}")

        # 验证客服属性
        assert result['name'] == cs_name, f"客服姓名错误: {result['name']} != {cs_name}"
        assert result['account'] == cs_account, f"客服账号错误: {result['account']} != {cs_account}"
        assert result['level'] == '6', f"客服级别错误: {result['level']} != '6'"
        assert result['user_id'] > 0, "用户ID无效"
        assert result['role_id'] > 0, "角色ID无效"

        print("虚拟客服创建测试通过！")

        # 测试获取虚拟客服列表
        cs_list = service.get_virtual_customer_services(page=1, size=10)
        print(f"当前虚拟客服总数: {cs_list['total']}")

        # 查找刚创建的客服
        found_cs = None
        for cs in cs_list['items']:
            if cs['account'] == cs_account:
                found_cs = cs
                break

        assert found_cs is not None, "未找到刚创建的虚拟客服"
        assert found_cs['level'] == '6', "虚拟客服级别错误"

        print("虚拟客服列表查询测试通过！")

        # 清理测试数据（软删除）
        delete_result = service.delete_virtual_customer_service(result['role_id'])
        assert delete_result['deleted'] == True, "虚拟客服删除失败"
        print("虚拟客服删除测试通过！\n")

    except Exception as e:
        print(f"虚拟客服测试失败: {str(e)}")
        raise
    finally:
        db.close()

def test_student_income_export():
    """测试学生收入导出"""
    print("=== 测试学生收入导出 ===")

    db = SessionLocal()
    service = VirtualOrderService(db)

    try:
        # 测试获取学生收入汇总
        summary = service.get_student_income_summary()

        print(f"学生收入汇总:")
        print(f"  学生总数: {summary['total_students']}")
        print(f"  任务总数: {summary['total_tasks']}")
        print(f"  总金额: {summary['total_amount']}")
        print(f"  已完成任务数: {summary['completed_tasks']}")
        print(f"  已完成金额: {summary['completed_amount']}")
        print(f"  完成率: {summary['completion_rate']}%")
        print(f"  统计时间: {summary['export_time']}")

        # 验证汇总数据
        assert summary['total_students'] >= 0, "学生总数不能为负数"
        assert summary['total_tasks'] >= 0, "任务总数不能为负数"
        assert summary['total_amount'] >= 0, "总金额不能为负数"
        assert summary['completed_tasks'] >= 0, "已完成任务数不能为负数"
        assert summary['completed_amount'] >= 0, "已完成金额不能为负数"
        assert 0 <= summary['completion_rate'] <= 100, "完成率应该在0-100之间"

        print("学生收入汇总测试通过！")

        # 测试导出Excel数据
        excel_data = service.export_student_income_data()

        print(f"Excel数据导出:")
        print(f"  数据大小: {len(excel_data)} 字节")

        # 验证Excel数据
        assert len(excel_data) > 0, "Excel数据不能为空"
        assert excel_data[:4] == b'PK\x03\x04', "Excel文件格式不正确"  # Excel文件的魔数

        print("学生收入导出测试通过！")

        # 可以选择保存测试文件（用于手动验证）
        # with open(f"test_export_{int(datetime.now().timestamp())}.xlsx", "wb") as f:
        #     f.write(excel_data)
        #     print(f"测试文件已保存: {f.name}")

        print("学生收入导出功能测试通过！\n")

    except Exception as e:
        print(f"学生收入导出测试失败: {str(e)}")
        raise
    finally:
        db.close()

def main():
    """主测试函数"""
    print("开始测试虚拟订单系统...")
    print("=" * 50)

    try:
        test_amount_calculation()
        test_order_number_generation()
        test_virtual_task_creation()
        test_multiple_tasks_generation()
        test_virtual_customer_service_creation()
        test_student_income_export()

        print("=" * 50)
        print("所有测试通过！虚拟订单系统基本功能正常。")

    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
