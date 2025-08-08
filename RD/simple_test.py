#!/usr/bin/env python3
"""
简单测试任务生成逻辑
"""

import json
import os
import random

def test_generation():
    """测试生成逻辑"""
    print("=== 简单测试任务生成逻辑 ===")
    
    # 获取配置文件目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, 'services', 'virtual_order_service', 'config')
    
    try:
        # 加载配置文件
        with open(os.path.join(config_dir, 'task_titles.json'), 'r', encoding='utf-8') as f:
            titles_data = json.load(f)
            task_titles = titles_data['titles']
        
        with open(os.path.join(config_dir, 'task_backgrounds.json'), 'r', encoding='utf-8') as f:
            backgrounds_data = json.load(f)
            task_backgrounds = backgrounds_data['backgrounds']
        
        with open(os.path.join(config_dir, 'task_styles.json'), 'r', encoding='utf-8') as f:
            styles_data = json.load(f)
            task_styles = styles_data['styles']
        
        print(f"✅ 配置加载成功:")
        print(f"   标题数量: {len(task_titles)}")
        print(f"   背景数量: {len(task_backgrounds)}")
        print(f"   风格数量: {len(task_styles)}")
        
        print(f"\n生成5个随机任务:")
        for i in range(5):
            # 随机选择
            title = random.choice(task_titles)
            background = random.choice(task_backgrounds)
            style = random.choice(task_styles)
            
            requirement = f"{background}，{style}"
            
            print(f"\n{i+1}. 标题: {title}")
            print(f"   描述: {requirement}")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generation()
