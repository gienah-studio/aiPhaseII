#!/usr/bin/env python3
"""
测试学员收入统计API
"""

import requests
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_student_income_stats():
    """测试学员收入统计接口"""
    
    # API基础URL
    base_url = "http://localhost:9001"  # auth_service端口
    
    # 1. 先登录获取token
    login_url = f"{base_url}/login"
    login_data = {
        "username": "admin",  # 使用admin账号测试
        "password": "123456"
    }
    
    print("1. 尝试登录...")
    try:
        login_response = requests.post(login_url, json=login_data)
        print(f"登录响应状态码: {login_response.status_code}")
        print(f"登录响应内容: {login_response.text}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            if login_result.get("code") == 200:
                token = login_result["data"]["accessToken"]
                print(f"登录成功，获取到token: {token[:20]}...")
                
                # 2. 调用学员收入统计接口
                stats_url = f"{base_url}/student/daily-income-stats"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                print("\n2. 调用学员收入统计接口...")
                stats_response = requests.get(stats_url, headers=headers)
                print(f"统计接口响应状态码: {stats_response.status_code}")
                print(f"统计接口响应内容: {stats_response.text}")
                
                if stats_response.status_code == 200:
                    stats_result = stats_response.json()
                    if stats_result.get("code") == 200:
                        data = stats_result["data"]
                        print("\n✅ 学员收入统计获取成功:")
                        print(f"  统计日期: {data['stat_date']}")
                        print(f"  学员总数: {data['total']}")
                        print(f"  学员列表:")
                        for i, student in enumerate(data['students'][:3]):  # 只显示前3个
                            print(f"    {i+1}. {student['student_name']} (ID:{student['student_id']})")
                            print(f"       昨日收入: ¥{student['yesterday_income']}")
                            print(f"       完成订单: {student['yesterday_completed_orders']}单")
                            print(f"       实际到手: ¥{student['actual_income']}")
                        if len(data['students']) > 3:
                            print(f"    ... 还有 {len(data['students']) - 3} 个学员")
                    else:
                        print(f"❌ 统计接口返回错误: {stats_result.get('message')}")
                else:
                    print(f"❌ 统计接口请求失败: {stats_response.status_code}")
            else:
                print(f"❌ 登录失败: {login_result.get('message')}")
        else:
            print(f"❌ 登录请求失败: {login_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保auth_service正在运行")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")

def test_with_mock_data():
    """使用模拟数据测试接口逻辑"""
    print("\n3. 测试接口逻辑（模拟数据）...")

    # 模拟返回的数据结构（按主系统逻辑）
    mock_response = {
        "code": 200,
        "message": "获取成功",
        "data": {
            "students": [
                {
                    "student_id": 123,
                    "student_name": "测试学员1",
                    "yesterday_income": "100.00",
                    "yesterday_completed_orders": 3,
                    "commission_rate": "0.75",
                    "actual_income": "75.00",
                    "phone_number": "13800138000",
                    "agent_id": 456
                },
                {
                    "student_id": 124,
                    "student_name": "测试学员2",
                    "yesterday_income": "50.00",
                    "yesterday_completed_orders": 2,
                    "commission_rate": "0.80",
                    "actual_income": "40.00",
                    "phone_number": "13800138001",
                    "agent_id": 456
                }
            ],
            "total": 2,
            "stat_date": "2024-01-15"
        }
    }

    print("✅ 模拟接口响应（按主系统逻辑）:")
    print(json.dumps(mock_response, indent=2, ensure_ascii=False))

    print("\n📝 计算逻辑说明:")
    print("1. yesterday_income: 原始佣金总额（任务佣金之和）")
    print("2. commission_rate: agent_rebate（学员能拿到的比例）")
    print("3. actual_income: yesterday_income × commission_rate")
    print("4. 任务筛选: status='4' 且 accepted_by 包含当前用户ID")

if __name__ == "__main__":
    print("🚀 开始测试学员收入统计API")
    print("=" * 50)
    
    test_student_income_stats()
    test_with_mock_data()
    
    print("\n" + "=" * 50)
    print("📝 测试完成")
    print("\n注意事项:")
    print("1. 确保auth_service服务正在运行 (端口9001)")
    print("2. 需要有效的学员账号进行测试")
    print("3. 数据库中需要有相关的任务数据")
