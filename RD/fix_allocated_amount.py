#!/usr/bin/env python3
"""
修复虚拟订单学生池中 allocated_amount 字段的计算错误

问题描述：
- allocated_amount 字段计算错误，导致显示的已分配金额不正确
- 正确逻辑应该是：allocated_amount = total_subsidy - remaining_amount

修复内容：
1. 重新计算所有学生池的 allocated_amount 字段
2. 确保数据逻辑一致性：total_subsidy = allocated_amount + remaining_amount
"""

import sys
import os
from decimal import Decimal
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.database import get_db
from shared.models.virtual_order_pool import VirtualOrderPool
from shared.models.tasks import Tasks
from sqlalchemy import and_


def fix_allocated_amount():
    """修复 allocated_amount 字段计算错误"""
    print("=== 开始修复虚拟订单池 allocated_amount 字段 ===")
    print()
    
    db = next(get_db())
    
    try:
        # 获取所有虚拟订单池
        pools = db.query(VirtualOrderPool).all()
        
        print(f"找到 {len(pools)} 个学生补贴池")
        print()
        
        fixed_count = 0
        
        for pool in pools:
            print(f"处理学生: {pool.student_name} (ID: {pool.student_id})")
            print(f"  修复前 - 总补贴: {pool.total_subsidy}, 已分配: {pool.allocated_amount}, 剩余: {pool.remaining_amount}, 已完成: {pool.completed_amount}")
            
            # 重新计算 allocated_amount
            # allocated_amount = total_subsidy - remaining_amount
            old_allocated = pool.allocated_amount
            new_allocated = pool.total_subsidy - pool.remaining_amount
            
            if old_allocated != new_allocated:
                pool.allocated_amount = new_allocated
                pool.updated_at = datetime.now()
                fixed_count += 1
                
                print(f"  修复后 - 总补贴: {pool.total_subsidy}, 已分配: {pool.allocated_amount}, 剩余: {pool.remaining_amount}, 已完成: {pool.completed_amount}")
                print(f"  ✅ 已修复 allocated_amount: {old_allocated} -> {new_allocated}")
            else:
                print(f"  ✓ allocated_amount 已正确: {pool.allocated_amount}")
            
            # 验证数据逻辑
            total_check = pool.allocated_amount + pool.remaining_amount
            if abs(total_check - pool.total_subsidy) > Decimal('0.01'):
                print(f"  ⚠️  警告: 数据逻辑不一致! allocated({pool.allocated_amount}) + remaining({pool.remaining_amount}) = {total_check} != total({pool.total_subsidy})")
            
            print()
        
        # 提交更改
        db.commit()
        
        print(f"=== 修复完成 ===")
        print(f"总计处理: {len(pools)} 个学生池")
        print(f"修复数量: {fixed_count} 个")
        print()
        
        # 显示修复后的统计
        print("=== 修复后数据验证 ===")
        pools = db.query(VirtualOrderPool).all()
        
        for pool in pools:
            total_check = pool.allocated_amount + pool.remaining_amount
            status = "✅ 正确" if abs(total_check - pool.total_subsidy) <= Decimal('0.01') else "❌ 错误"
            print(f"{pool.student_name}: 总补贴={pool.total_subsidy}, 已分配={pool.allocated_amount}, 剩余={pool.remaining_amount} - {status}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 修复过程中出错: {str(e)}")
        raise
    finally:
        db.close()


def verify_data_consistency():
    """验证数据一致性"""
    print("=== 验证虚拟订单池数据一致性 ===")
    print()
    
    db = next(get_db())
    
    try:
        pools = db.query(VirtualOrderPool).all()
        
        inconsistent_count = 0
        
        for pool in pools:
            # 检查基本逻辑：total_subsidy = allocated_amount + remaining_amount
            total_check = pool.allocated_amount + pool.remaining_amount
            
            if abs(total_check - pool.total_subsidy) > Decimal('0.01'):
                inconsistent_count += 1
                print(f"❌ {pool.student_name}: 数据不一致")
                print(f"   总补贴: {pool.total_subsidy}")
                print(f"   已分配: {pool.allocated_amount}")
                print(f"   剩余: {pool.remaining_amount}")
                print(f"   计算结果: {total_check} (应该等于总补贴)")
                print()
            else:
                print(f"✅ {pool.student_name}: 数据一致")
        
        print(f"=== 验证结果 ===")
        print(f"总计检查: {len(pools)} 个学生池")
        print(f"数据不一致: {inconsistent_count} 个")
        
        if inconsistent_count == 0:
            print("🎉 所有数据都是一致的！")
        else:
            print("⚠️  发现数据不一致，建议运行修复脚本")
        
    except Exception as e:
        print(f"❌ 验证过程中出错: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="修复虚拟订单池 allocated_amount 字段")
    parser.add_argument("--verify", action="store_true", help="仅验证数据一致性，不进行修复")
    parser.add_argument("--fix", action="store_true", help="执行数据修复")
    
    args = parser.parse_args()
    
    if args.verify:
        verify_data_consistency()
    elif args.fix:
        fix_allocated_amount()
    else:
        print("请指定操作:")
        print("  --verify  验证数据一致性")
        print("  --fix     修复数据")
        print()
        print("示例:")
        print("  python fix_allocated_amount.py --verify")
        print("  python fix_allocated_amount.py --fix")
