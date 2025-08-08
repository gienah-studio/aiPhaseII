#!/usr/bin/env python3
"""
快速测试虚拟任务生成
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from services.virtual_order_service.service.virtual_order_service import VirtualOrderService

def quick_test():
    """快速测试任务内容生成"""
    print("=== 快速测试虚拟任务生成 ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    print("测试配置加载状态:")
    print(f"标题数量: {len(service.task_titles)}")
    print(f"背景数量: {len(service.task_backgrounds)}")
    print(f"风格数量: {len(service.task_styles)}")
    print(f"模板数据: {'已加载' if service.task_templates_data else '未加载'}")
    
    print("\n生成5个随机任务内容:")
    for i in range(5):
        content = service.generate_random_task_content()
        print(f"\n{i+1}. 标题: {content['summary']}")
        print(f"   描述: {content['requirement']}")
    
    db.close()

if __name__ == "__main__":
    quick_test()
