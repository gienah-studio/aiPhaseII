#!/usr/bin/env python3
"""
测试新的登录逻辑
"""
import requests
import json

# 测试登录接口
def test_login():
    url = "http://localhost:9005/auth/login"
    
    # 测试数据
    test_data = {
        "username": "admin",
        "password": "admin"
    }
    
    try:
        response = requests.post(url, json=test_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✅ 登录测试成功!")
            return response.json()
        else:
            print("❌ 登录测试失败!")
            return None
            
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None

if __name__ == "__main__":
    print("开始测试新的登录逻辑...")
    test_login()
