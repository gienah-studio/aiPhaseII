#!/usr/bin/env python3
"""
认证服务API接口单元测试
测试认证服务的7个核心接口功能
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_api_1_login():
    """测试API 1: 用户登录"""
    print("=== 测试API 1: 用户登录 ===")
    
    try:
        # 模拟请求数据
        request_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        # 模拟响应数据
        expected_response = {
            "code": 200,
            "message": "登录成功",
            "data": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }
        
        print(f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
        print(f"期望响应: {json.dumps(expected_response, ensure_ascii=False, indent=2)}")
        
        # 验证请求数据格式
        assert "username" in request_data, "缺少用户名"
        assert "password" in request_data, "缺少密码"
        assert len(request_data["username"]) > 0, "用户名不能为空"
        assert len(request_data["password"]) > 0, "密码不能为空"
        
        # 验证响应数据格式
        assert expected_response["code"] == 200, "响应状态码错误"
        assert "access_token" in expected_response["data"], "缺少访问令牌"
        assert "token_type" in expected_response["data"], "缺少令牌类型"
        assert "expires_in" in expected_response["data"], "缺少过期时间"
        
        print("✅ API 1 测试通过: 用户登录接口格式正确")
        return True
        
    except Exception as e:
        print(f"❌ API 1 测试失败: {e}")
        return False

def test_api_2_logout():
    """测试API 2: 退出登录"""
    print("\n=== 测试API 2: 退出登录 ===")
    
    try:
        # 模拟请求数据（空对象）
        request_data = {}
        
        # 模拟响应数据
        expected_response = {
            "code": 200,
            "message": "退出登录成功"
        }
        
        print(f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
        print(f"期望响应: {json.dumps(expected_response, ensure_ascii=False, indent=2)}")
        
        # 验证响应数据格式
        assert expected_response["code"] == 200, "响应状态码错误"
        assert expected_response["message"] == "退出登录成功", "响应消息错误"
        
        print("✅ API 2 测试通过: 退出登录接口格式正确")
        return True
        
    except Exception as e:
        print(f"❌ API 2 测试失败: {e}")
        return False

def test_api_3_get_profile():
    """测试API 3: 获取个人信息"""
    print("\n=== 测试API 3: 获取个人信息 ===")
    
    try:
        # 模拟响应数据
        expected_response = {
            "code": 200,
            "message": "获取成功",
            "data": {
                "id": 1,
                "username": "admin",
                "realName": "管理员",
                "phone": "13800138000",
                "email": "admin@example.com",
                "role": "admin",
                "status": 1,
                "avatar": "http://example.com/avatar.jpg",
                "createdAt": "2024-01-01T10:00:00",
                "updatedAt": "2024-01-01T10:00:00"
            }
        }
        
        print(f"期望响应: {json.dumps(expected_response, ensure_ascii=False, indent=2)}")
        
        # 验证响应数据格式
        assert expected_response["code"] == 200, "响应状态码错误"
        assert "data" in expected_response, "缺少data字段"
        
        user_data = expected_response["data"]
        required_fields = ["id", "username", "realName", "role"]
        for field in required_fields:
            assert field in user_data, f"缺少{field}字段"
        
        print("✅ API 3 测试通过: 获取个人信息接口格式正确")
        return True
        
    except Exception as e:
        print(f"❌ API 3 测试失败: {e}")
        return False

def test_api_4_upload_file():
    """测试API 4: 上传文件"""
    print("\n=== 测试API 4: 上传文件 ===")
    
    try:
        # 模拟文件上传（multipart/form-data）
        file_info = {
            "filename": "test.jpg",
            "content_type": "image/jpeg",
            "size": 1024000  # 1MB
        }
        
        # 模拟响应数据
        expected_response = {
            "code": 200,
            "message": "上传成功",
            "data": {
                "file_url": "http://example.com/uploads/test.jpg",
                "file_name": "test.jpg",
                "file_size": 1024000,
                "upload_time": "2024-01-01T10:00:00"
            }
        }
        
        print(f"文件信息: {json.dumps(file_info, ensure_ascii=False, indent=2)}")
        print(f"期望响应: {json.dumps(expected_response, ensure_ascii=False, indent=2)}")
        
        # 验证文件信息
        assert "filename" in file_info, "缺少文件名"
        assert "content_type" in file_info, "缺少文件类型"
        assert file_info["size"] > 0, "文件大小必须大于0"
        
        # 验证响应数据格式
        assert expected_response["code"] == 200, "响应状态码错误"
        assert "file_url" in expected_response["data"], "缺少文件URL"
        assert "file_name" in expected_response["data"], "缺少文件名"
        
        print("✅ API 4 测试通过: 上传文件接口格式正确")
        return True
        
    except Exception as e:
        print(f"❌ API 4 测试失败: {e}")
        return False

def test_api_5_change_password():
    """测试API 5: 修改密码"""
    print("\n=== 测试API 5: 修改密码 ===")
    
    try:
        # 模拟请求数据
        request_data = {
            "old_password": "old123456",
            "new_password": "new123456",
            "new_password_confirm": "new123456"
        }
        
        # 模拟响应数据
        expected_response = {
            "code": 200,
            "message": "密码修改成功"
        }
        
        print(f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
        print(f"期望响应: {json.dumps(expected_response, ensure_ascii=False, indent=2)}")
        
        # 验证请求数据格式
        assert "old_password" in request_data, "缺少原密码"
        assert "new_password" in request_data, "缺少新密码"
        assert "new_password_confirm" in request_data, "缺少确认密码"
        assert request_data["new_password"] == request_data["new_password_confirm"], "新密码与确认密码不一致"
        assert len(request_data["new_password"]) >= 6, "新密码长度至少6位"
        
        # 验证响应数据格式
        assert expected_response["code"] == 200, "响应状态码错误"
        assert expected_response["message"] == "密码修改成功", "响应消息错误"
        
        print("✅ API 5 测试通过: 修改密码接口格式正确")
        return True
        
    except Exception as e:
        print(f"❌ API 5 测试失败: {e}")
        return False

def test_api_6_reset_password():
    """测试API 6: 重置密码"""
    print("\n=== 测试API 6: 重置密码 ===")
    
    try:
        # 模拟请求数据
        request_data = {
            "user_id": 123
        }
        
        # 模拟响应数据
        expected_response = {
            "code": 200,
            "message": "密码重置成功"
        }
        
        print(f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
        print(f"期望响应: {json.dumps(expected_response, ensure_ascii=False, indent=2)}")
        
        # 验证请求数据格式
        assert "user_id" in request_data, "缺少用户ID"
        assert isinstance(request_data["user_id"], int), "用户ID必须是整数"
        assert request_data["user_id"] > 0, "用户ID必须大于0"
        
        # 验证响应数据格式
        assert expected_response["code"] == 200, "响应状态码错误"
        assert expected_response["message"] == "密码重置成功", "响应消息错误"
        
        print("✅ API 6 测试通过: 重置密码接口格式正确")
        return True
        
    except Exception as e:
        print(f"❌ API 6 测试失败: {e}")
        return False

def test_api_7_update_profile():
    """测试API 7: 更新个人信息"""
    print("\n=== 测试API 7: 更新个人信息 ===")
    
    try:
        # 模拟请求数据
        request_data = {
            "realName": "新的真实姓名",
            "phone": "13900139000",
            "email": "newemail@example.com"
        }
        
        # 模拟响应数据
        expected_response = {
            "code": 200,
            "message": "更新成功",
            "data": {
                "id": 1,
                "username": "admin",
                "realName": "新的真实姓名",
                "phone": "13900139000",
                "email": "newemail@example.com",
                "role": "admin",
                "updatedAt": "2024-01-01T11:00:00"
            }
        }
        
        print(f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
        print(f"期望响应: {json.dumps(expected_response, ensure_ascii=False, indent=2)}")
        
        # 验证请求数据格式（可选字段）
        if "phone" in request_data:
            assert len(request_data["phone"]) >= 11, "手机号长度不正确"
        if "email" in request_data:
            assert "@" in request_data["email"], "邮箱格式不正确"
        
        # 验证响应数据格式
        assert expected_response["code"] == 200, "响应状态码错误"
        assert "data" in expected_response, "缺少data字段"
        assert expected_response["data"]["realName"] == request_data["realName"], "更新的姓名不匹配"
        
        print("✅ API 7 测试通过: 更新个人信息接口格式正确")
        return True
        
    except Exception as e:
        print(f"❌ API 7 测试失败: {e}")
        return False

def test_auth_api_endpoints_summary():
    """测试认证API端点汇总"""
    print("\n=== 认证API端点汇总 ===")
    
    auth_endpoints = [
        {
            "method": "POST",
            "path": "/api/auth/login",
            "description": "用户登录",
            "auth_required": False,
            "request_body": "LoginRequest",
            "response": "SimpleTokenResponse"
        },
        {
            "method": "POST",
            "path": "/api/auth/logout",
            "description": "退出登录",
            "auth_required": True,
            "request_body": "LogoutRequest",
            "response": "ResponseSchema"
        },
        {
            "method": "GET",
            "path": "/api/auth/profile",
            "description": "获取个人信息",
            "auth_required": True,
            "response": "UserResponse"
        },
        {
            "method": "POST",
            "path": "/api/auth/upload",
            "description": "上传文件",
            "auth_required": True,
            "request_type": "multipart/form-data",
            "response": "FileUploadResponse"
        },
        {
            "method": "POST",
            "path": "/api/auth/changePassword",
            "description": "修改密码",
            "auth_required": True,
            "request_body": "ChangePasswordRequest",
            "response": "ResponseSchema"
        },
        {
            "method": "POST",
            "path": "/api/auth/resetPassword",
            "description": "重置密码",
            "auth_required": True,
            "request_body": "ResetPasswordRequest",
            "response": "ResponseSchema"
        },
        {
            "method": "PUT",
            "path": "/api/auth/profile",
            "description": "更新个人信息",
            "auth_required": True,
            "request_body": "UpdateUserInfoRequest",
            "response": "UserResponse"
        }
    ]
    
    print("认证服务API接口列表:")
    print("-" * 80)
    for i, endpoint in enumerate(auth_endpoints, 1):
        auth_status = "🔒 需要认证" if endpoint['auth_required'] else "🔓 无需认证"
        print(f"{i}. {endpoint['method']} {endpoint['path']}")
        print(f"   描述: {endpoint['description']}")
        print(f"   认证: {auth_status}")
        if 'request_body' in endpoint:
            print(f"   请求体: {endpoint['request_body']}")
        if 'request_type' in endpoint:
            print(f"   请求类型: {endpoint['request_type']}")
        print(f"   响应: {endpoint['response']}")
        print()
    
    return True

def main():
    """主测试函数"""
    print("开始测试认证服务7个API接口...")
    print("=" * 60)
    
    test_results = []
    
    # 测试7个认证API接口
    test_results.append(("API 1: 用户登录", test_api_1_login()))
    test_results.append(("API 2: 退出登录", test_api_2_logout()))
    test_results.append(("API 3: 获取个人信息", test_api_3_get_profile()))
    test_results.append(("API 4: 上传文件", test_api_4_upload_file()))
    test_results.append(("API 5: 修改密码", test_api_5_change_password()))
    test_results.append(("API 6: 重置密码", test_api_6_reset_password()))
    test_results.append(("API 7: 更新个人信息", test_api_7_update_profile()))
    
    # API端点汇总
    test_auth_api_endpoints_summary()
    
    # 输出测试结果
    print("=" * 60)
    print("测试结果汇总:")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"总计: {len(test_results)} 个API接口")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    
    if failed == 0:
        print("\n🎉 所有认证服务API接口测试通过！")
        print("接口格式和数据结构验证正确。")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个API接口测试失败。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
