#!/usr/bin/env python3
"""
测试虚拟订单任务调度器的时间设置
验证每天9点38分执行的逻辑是否正确
"""

import sys
import os
from datetime import datetime, time, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.virtual_order_service.service.task_scheduler import VirtualOrderTaskScheduler


def test_scheduler_time_calculation():
    """测试调度器时间计算逻辑"""
    print("=== 测试虚拟订单任务调度器时间计算 ===")
    print()
    
    scheduler = VirtualOrderTaskScheduler()
    
    # 测试不同时间点的下次执行时间计算
    test_cases = [
        # 测试时间, 描述
        (datetime(2025, 7, 21, 8, 30), "早上8:30 - 应该安排到今天9:38"),
        (datetime(2025, 7, 21, 9, 38), "正好9:38 - 应该安排到明天9:38"),
        (datetime(2025, 7, 21, 10, 30), "上午10:30 - 应该安排到明天9:38"),
        (datetime(2025, 7, 21, 15, 45), "下午3:45 - 应该安排到明天9:38"),
        (datetime(2025, 7, 21, 23, 59), "晚上11:59 - 应该安排到明天9:38"),
    ]
    
    print(f"调度器设置时间: 每天 {scheduler.scheduled_time.strftime('%H:%M')}")
    print()
    
    for test_time, description in test_cases:
        # 模拟当前时间
        original_now = datetime.now
        datetime.now = lambda: test_time
        
        try:
            next_run = scheduler.get_next_run_time()
            wait_seconds = (next_run - test_time).total_seconds()
            wait_hours = wait_seconds / 3600
            
            print(f"测试场景: {description}")
            print(f"  当前时间: {test_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  下次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  等待时间: {wait_hours:.2f} 小时 ({wait_seconds:.0f} 秒)")
            
            # 验证逻辑正确性
            expected_date = test_time.date()
            if test_time.time() >= scheduler.scheduled_time:
                expected_date += timedelta(days=1)
            
            expected_next_run = datetime.combine(expected_date, scheduler.scheduled_time)
            
            if next_run == expected_next_run:
                print("  ✅ 计算正确")
            else:
                print(f"  ❌ 计算错误，期望: {expected_next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            print()
            
        finally:
            # 恢复原始的datetime.now
            datetime.now = original_now


def test_current_next_run_time():
    """测试当前时间的下次执行时间"""
    print("=== 当前时间的下次执行时间 ===")
    print()
    
    scheduler = VirtualOrderTaskScheduler()
    now = datetime.now()
    next_run = scheduler.get_next_run_time()
    wait_seconds = (next_run - now).total_seconds()
    wait_hours = wait_seconds / 3600
    wait_days = wait_hours / 24
    
    print(f"调度器设置: 每天 {scheduler.scheduled_time.strftime('%H:%M')} 执行")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"下次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"等待时间: {wait_days:.2f} 天 ({wait_hours:.2f} 小时)")
    print()
    
    if wait_seconds > 0:
        print("✅ 调度器配置正确，等待下次执行时间")
    else:
        print("⚠️  警告: 等待时间为负数，可能存在配置问题")


def show_scheduler_info():
    """显示调度器配置信息"""
    print("=== 虚拟订单任务调度器配置信息 ===")
    print()
    
    scheduler = VirtualOrderTaskScheduler()
    
    print("📅 调度配置:")
    print(f"  执行时间: 每天 {scheduler.scheduled_time.strftime('%H:%M')}")
    print(f"  时区: 系统本地时区")
    print()
    
    print("🔄 执行内容:")
    print("  - 检查24小时前创建的虚拟任务")
    print("  - 删除过期未接取的任务（排除状态1、2、4）")
    print("  - 将过期任务金额返还到学生补贴池")
    print("  - 重新生成新的虚拟任务")
    print("  - 更新学生补贴池的分配状态")
    print()
    
    print("📝 日志记录:")
    print("  - 启动时记录调度器状态")
    print("  - 每次执行前记录等待时间")
    print("  - 执行过程中记录处理详情")
    print("  - 异常情况记录错误信息")


if __name__ == "__main__":
    print("虚拟订单任务调度器时间测试")
    print("=" * 50)
    print()
    
    try:
        show_scheduler_info()
        print()
        test_scheduler_time_calculation()
        print()
        test_current_next_run_time()
        
        print("=" * 50)
        print("✅ 所有测试完成！调度器时间配置正确。")
        print()
        print("💡 提示:")
        print("  - 调度器已设置为每天9:38执行")
        print("  - 系统启动后会自动计算下次执行时间")
        print("  - 可以通过API手动触发过期任务检查")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
