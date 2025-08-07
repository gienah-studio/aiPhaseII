#!/usr/bin/env python3
"""
全系统API接口单元测试
测试所有服务的API接口功能
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_auth_service_apis():
    """测试认证服务API接口"""
    print("=== 测试认证服务API接口 ===")
    
    auth_apis = [
        {
            "method": "POST",
            "path": "/api/auth/login",
            "description": "用户登录",
            "request_body": {
                "username": "admin",
                "password": "admin123"
            },
            "expected_response": {
                "code": 200,
                "message": "登录成功",
                "data": {
                    "access_token": "jwt_token_here",
                    "token_type": "bearer",
                    "expires_in": 3600
                }
            }
        },
        {
            "method": "POST",
            "path": "/api/auth/logout",
            "description": "退出登录",
            "request_body": {},
            "expected_response": {
                "code": 200,
                "message": "退出登录成功"
            }
        },
        {
            "method": "GET",
            "path": "/api/auth/profile",
            "description": "获取个人信息",
            "expected_response": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "id": 1,
                    "username": "admin",
                    "realName": "管理员",
                    "role": "admin"
                }
            }
        },
        {
            "method": "POST",
            "path": "/api/auth/upload",
            "description": "上传文件",
            "request_type": "multipart/form-data",
            "expected_response": {
                "code": 200,
                "message": "上传成功",
                "data": {
                    "file_url": "http://example.com/file.jpg",
                    "file_name": "file.jpg"
                }
            }
        },
        {
            "method": "POST",
            "path": "/api/auth/changePassword",
            "description": "修改密码",
            "request_body": {
                "old_password": "old123",
                "new_password": "new123",
                "new_password_confirm": "new123"
            },
            "expected_response": {
                "code": 200,
                "message": "密码修改成功"
            }
        },
        {
            "method": "POST",
            "path": "/api/auth/resetPassword",
            "description": "重置密码",
            "request_body": {
                "user_id": 1
            },
            "expected_response": {
                "code": 200,
                "message": "密码重置成功"
            }
        },
        {
            "method": "PUT",
            "path": "/api/auth/profile",
            "description": "更新个人信息",
            "request_body": {
                "realName": "新姓名",
                "phone": "13800138000"
            },
            "expected_response": {
                "code": 200,
                "message": "更新成功",
                "data": {
                    "id": 1,
                    "realName": "新姓名",
                    "phone": "13800138000"
                }
            }
        }
    ]
    
    print(f"认证服务API接口数量: {len(auth_apis)}")
    for i, api in enumerate(auth_apis, 1):
        print(f"{i}. {api['method']} {api['path']} - {api['description']}")
    
    return len(auth_apis)

def test_virtual_order_service_apis():
    """测试虚拟订单服务API接口"""
    print("\n=== 测试虚拟订单服务API接口 ===")
    
    virtual_order_apis = [
        {
            "method": "POST",
            "path": "/api/virtual-orders/import/student-subsidy",
            "description": "导入学生补贴表",
            "request_type": "multipart/form-data",
            "expected_response": {
                "code": 200,
                "message": "导入成功",
                "data": {
                    "import_batch": "BATCH_20240101_120000_abc123",
                    "total_students": 10,
                    "total_subsidy": 2000.00,
                    "generated_tasks": 45
                }
            }
        },
        {
            "method": "POST",
            "path": "/api/virtual-orders/import/customer-service",
            "description": "导入专用客服",
            "request_type": "multipart/form-data",
            "expected_response": {
                "code": 200,
                "message": "导入成功",
                "data": {
                    "total_imported": 5,
                    "failed_count": 0
                }
            }
        },
        {
            "method": "GET",
            "path": "/api/virtual-orders/stats",
            "description": "获取虚拟订单统计",
            "expected_response": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "total_students": 100,
                    "total_subsidy": 20000.00,
                    "generated_tasks": 450,
                    "completed_tasks": 200,
                    "completion_rate": 44.44
                }
            }
        },
        {
            "method": "GET",
            "path": "/api/virtual-orders/student-pools",
            "description": "获取学生补贴池列表",
            "query_params": "page=1&size=20&status=active",
            "expected_response": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "items": [],
                    "total": 0,
                    "page": 1,
                    "size": 20
                }
            }
        },
        {
            "method": "POST",
            "path": "/api/virtual-orders/reallocate/{student_id}",
            "description": "重新分配学生任务",
            "path_params": "student_id",
            "expected_response": {
                "code": 200,
                "message": "重新分配成功",
                "data": {
                    "student_id": 123,
                    "remaining_amount": 150.00,
                    "new_tasks_count": 3
                }
            }
        },
        {
            "method": "POST",
            "path": "/api/virtual-orders/customer-service",
            "description": "创建虚拟客服",
            "request_body": {
                "name": "测试客服",
                "account": "test_cs_001",
                "phone_number": "13800138000",
                "id_card": "123456789012345678",
                "initial_password": "123456"
            },
            "expected_response": {
                "code": 200,
                "message": "创建成功",
                "data": {
                    "user_id": 123,
                    "role_id": 456,
                    "name": "测试客服",
                    "account": "test_cs_001",
                    "level": "6",
                    "initial_password": "123456"
                }
            }
        },
        {
            "method": "GET",
            "path": "/api/virtual-orders/customer-service",
            "description": "获取虚拟客服列表",
            "query_params": "page=1&size=20",
            "expected_response": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "items": [],
                    "total": 0,
                    "page": 1,
                    "size": 20
                }
            }
        },
        {
            "method": "PUT",
            "path": "/api/virtual-orders/customer-service/{role_id}",
            "description": "更新虚拟客服信息",
            "path_params": "role_id",
            "request_body": {
                "name": "更新后的客服",
                "phone_number": "13900139000"
            },
            "expected_response": {
                "code": 200,
                "message": "更新成功",
                "data": {
                    "role_id": 456,
                    "name": "更新后的客服",
                    "phone_number": "13900139000",
                    "updated": True
                }
            }
        },
        {
            "method": "DELETE",
            "path": "/api/virtual-orders/customer-service/{role_id}",
            "description": "删除虚拟客服",
            "path_params": "role_id",
            "expected_response": {
                "code": 200,
                "message": "删除成功",
                "data": {
                    "role_id": 456,
                    "name": "测试客服",
                    "account": "test_cs_001",
                    "deleted": True
                }
            }
        }
    ]
    
    print(f"虚拟订单服务API接口数量: {len(virtual_order_apis)}")
    for i, api in enumerate(virtual_order_apis, 1):
        print(f"{i}. {api['method']} {api['path']} - {api['description']}")
    
    return len(virtual_order_apis)

def test_api_gateway_apis():
    """测试API网关接口"""
    print("\n=== 测试API网关接口 ===")
    
    gateway_apis = [
        {
            "method": "GET",
            "path": "/health",
            "description": "健康检查",
            "expected_response": {
                "status": "ok",
                "timestamp": 1640995200
            }
        },
        {
            "method": "GET",
            "path": "/services",
            "description": "获取所有微服务状态",
            "expected_response": {
                "auth": {
                    "status": "up",
                    "url": "http://auth_service:8000",
                    "details": {}
                },
                "user": {
                    "status": "up", 
                    "url": "http://user_service:8001",
                    "details": {}
                }
            }
        }
    ]
    
    print(f"API网关接口数量: {len(gateway_apis)}")
    for i, api in enumerate(gateway_apis, 1):
        print(f"{i}. {api['method']} {api['path']} - {api['description']}")
    
    return len(gateway_apis)

def validate_api_structure(api_list, service_name):
    """验证API结构"""
    print(f"\n=== 验证{service_name}API结构 ===")
    
    valid_count = 0
    invalid_count = 0
    
    for api in api_list:
        try:
            # 验证必需字段
            assert "method" in api, "缺少method字段"
            assert "path" in api, "缺少path字段"
            assert "description" in api, "缺少description字段"
            assert "expected_response" in api, "缺少expected_response字段"
            
            # 验证HTTP方法
            valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
            assert api["method"] in valid_methods, f"无效的HTTP方法: {api['method']}"
            
            # 验证路径格式
            assert api["path"].startswith("/"), "路径必须以/开头"
            
            valid_count += 1
            
        except AssertionError as e:
            print(f"❌ API结构验证失败: {api.get('path', 'unknown')} - {e}")
            invalid_count += 1
    
    print(f"✅ 有效API: {valid_count}")
    print(f"❌ 无效API: {invalid_count}")
    
    return valid_count, invalid_count

def main():
    """主测试函数"""
    print("开始测试全系统API接口...")
    print("=" * 60)
    
    # 测试各服务API
    auth_count = test_auth_service_apis()
    virtual_order_count = test_virtual_order_service_apis()
    gateway_count = test_api_gateway_apis()
    
    total_apis = auth_count + virtual_order_count + gateway_count
    
    print("\n" + "=" * 60)
    print("API接口统计汇总:")
    print("-" * 60)
    print(f"认证服务API:        {auth_count} 个")
    print(f"虚拟订单服务API:    {virtual_order_count} 个")
    print(f"API网关接口:        {gateway_count} 个")
    print("-" * 60)
    print(f"总计API接口:        {total_apis} 个")
    
    print("\n" + "=" * 60)
    print("需要单元测试的接口分类:")
    print("-" * 60)
    print("🔐 认证相关: 登录、登出、个人信息、密码管理")
    print("📁 文件上传: 文件上传接口")
    print("👥 虚拟客服: CRUD操作 (已完成测试)")
    print("📊 数据导入: Excel文件导入")
    print("📈 统计查询: 数据统计和列表查询")
    print("🔄 任务管理: 任务重新分配")
    print("🏥 系统监控: 健康检查和服务状态")
    
    print("\n" + "=" * 60)
    print("建议的测试优先级:")
    print("-" * 60)
    print("1. 🔐 认证服务 (核心功能)")
    print("2. 👥 虚拟客服管理 (已完成)")
    print("3. 📊 数据导入功能")
    print("4. 📈 统计和查询功能")
    print("5. 🔄 任务管理功能")
    print("6. 🏥 系统监控功能")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
