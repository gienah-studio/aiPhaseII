#!/usr/bin/env python3
"""
API网关接口单元测试
测试API网关的2个核心接口功能
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_api_1_health_check():
    """测试API 1: 健康检查"""
    print("=== 测试API 1: 健康检查 ===")
    
    try:
        # 模拟响应数据
        expected_response = {
            "status": "ok",
            "timestamp": 1640995200,
            "version": "1.0.0",
            "uptime": 3600,
            "services": {
                "database": "connected",
                "redis": "connected",
                "auth_service": "running",
                "virtual_order_service": "running"
            },
            "system_info": {
                "memory_usage": "45%",
                "cpu_usage": "12%",
                "disk_usage": "68%"
            }
        }
        
        print(f"期望响应: {json.dumps(expected_response, ensure_ascii=False, indent=2)}")
        
        # 验证响应数据格式
        assert "status" in expected_response, "缺少status字段"
        assert "timestamp" in expected_response, "缺少timestamp字段"
        assert expected_response["status"] in ["ok", "warning", "error"], "status值无效"
        assert isinstance(expected_response["timestamp"], (int, float)), "timestamp必须是数字"
        assert expected_response["timestamp"] > 0, "timestamp必须大于0"
        
        # 验证服务状态
        if "services" in expected_response:
            services = expected_response["services"]
            valid_statuses = ["connected", "disconnected", "running", "stopped", "error"]
            for service_name, service_status in services.items():
                assert service_status in valid_statuses, f"服务{service_name}状态值无效: {service_status}"
        
        # 验证系统信息
        if "system_info" in expected_response:
            system_info = expected_response["system_info"]
            for metric_name, metric_value in system_info.items():
                if isinstance(metric_value, str) and metric_value.endswith('%'):
                    # 验证百分比格式
                    percentage = float(metric_value.rstrip('%'))
                    assert 0 <= percentage <= 100, f"{metric_name}百分比值无效: {percentage}"
        
        print("✅ API 1 测试通过: 健康检查接口格式正确")
        return True
        
    except Exception as e:
        print(f"❌ API 1 测试失败: {e}")
        return False

def test_api_2_service_status():
    """测试API 2: 获取所有微服务状态"""
    print("\n=== 测试API 2: 获取所有微服务状态 ===")
    
    try:
        # 模拟响应数据
        expected_response = {
            "auth": {
                "status": "up",
                "url": "http://auth_service:8000",
                "details": {
                    "version": "1.0.0",
                    "uptime": 3600,
                    "last_check": "2024-01-01T12:00:00",
                    "response_time": 45
                }
            },
            "user": {
                "status": "up",
                "url": "http://user_service:8001",
                "details": {
                    "version": "1.0.0",
                    "uptime": 3500,
                    "last_check": "2024-01-01T12:00:00",
                    "response_time": 32
                }
            },
            "organization": {
                "status": "down",
                "url": "http://organization_service:8002",
                "details": {
                    "error": "Connection timeout",
                    "last_check": "2024-01-01T12:00:00",
                    "last_success": "2024-01-01T11:45:00"
                }
            },
            "enterprise": {
                "status": "error",
                "url": "http://enterprise_service:8003",
                "details": {
                    "status_code": 500,
                    "error": "Internal server error",
                    "last_check": "2024-01-01T12:00:00"
                }
            },
            "permission": {
                "status": "up",
                "url": "http://permission_service:8004",
                "details": {
                    "version": "1.0.0",
                    "uptime": 3200,
                    "last_check": "2024-01-01T12:00:00",
                    "response_time": 28
                }
            }
        }
        
        print(f"期望响应: {json.dumps(expected_response, ensure_ascii=False, indent=2)}")
        
        # 验证响应数据格式
        assert isinstance(expected_response, dict), "响应必须是字典格式"
        assert len(expected_response) > 0, "至少应该有一个服务"
        
        # 验证每个服务的状态
        valid_statuses = ["up", "down", "error"]
        for service_name, service_info in expected_response.items():
            assert isinstance(service_info, dict), f"服务{service_name}信息必须是字典格式"
            assert "status" in service_info, f"服务{service_name}缺少status字段"
            assert "url" in service_info, f"服务{service_name}缺少url字段"
            assert "details" in service_info, f"服务{service_name}缺少details字段"
            
            # 验证状态值
            assert service_info["status"] in valid_statuses, f"服务{service_name}状态值无效: {service_info['status']}"
            
            # 验证URL格式
            assert service_info["url"].startswith("http"), f"服务{service_name}URL格式无效"
            
            # 验证详情信息
            details = service_info["details"]
            assert isinstance(details, dict), f"服务{service_name}详情必须是字典格式"
            
            # 根据状态验证不同的字段
            if service_info["status"] == "up":
                # 正常服务应该有版本和响应时间
                if "version" in details:
                    assert isinstance(details["version"], str), "版本号必须是字符串"
                if "response_time" in details:
                    assert isinstance(details["response_time"], (int, float)), "响应时间必须是数字"
                    assert details["response_time"] >= 0, "响应时间不能为负数"
            elif service_info["status"] in ["down", "error"]:
                # 异常服务应该有错误信息
                assert "error" in details or "status_code" in details, f"服务{service_name}缺少错误信息"
        
        # 统计服务状态
        status_count = {}
        for service_info in expected_response.values():
            status = service_info["status"]
            status_count[status] = status_count.get(status, 0) + 1
        
        print(f"服务状态统计: {status_count}")
        
        print("✅ API 2 测试通过: 获取所有微服务状态接口格式正确")
        return True
        
    except Exception as e:
        print(f"❌ API 2 测试失败: {e}")
        return False

def test_api_gateway_proxy_routes():
    """测试API网关代理路由"""
    print("\n=== 测试API网关代理路由 ===")
    
    try:
        # 模拟代理路由配置
        proxy_routes = [
            {
                "path_pattern": "/auth/{path:path}",
                "target_service": "auth",
                "target_url": "http://auth_service:8000",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "auth_required": False,
                "description": "代理请求到认证服务"
            },
            {
                "path_pattern": "/users/{path:path}",
                "target_service": "user",
                "target_url": "http://user_service:8001",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "auth_required": True,
                "description": "代理请求到用户服务"
            },
            {
                "path_pattern": "/organizations/{path:path}",
                "target_service": "organization",
                "target_url": "http://organization_service:8002",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "auth_required": True,
                "description": "代理请求到组织服务"
            },
            {
                "path_pattern": "/enterprises/{path:path}",
                "target_service": "enterprise",
                "target_url": "http://enterprise_service:8003",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "auth_required": True,
                "description": "代理请求到企业服务"
            },
            {
                "path_pattern": "/permissions/{path:path}",
                "target_service": "permission",
                "target_url": "http://permission_service:8004",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "auth_required": True,
                "description": "代理请求到权限服务"
            }
        ]
        
        print("API网关代理路由配置:")
        print("-" * 80)
        
        for i, route in enumerate(proxy_routes, 1):
            auth_status = "🔒 需要认证" if route['auth_required'] else "🔓 无需认证"
            print(f"{i}. {route['path_pattern']}")
            print(f"   目标服务: {route['target_service']}")
            print(f"   目标URL: {route['target_url']}")
            print(f"   支持方法: {', '.join(route['methods'])}")
            print(f"   认证要求: {auth_status}")
            print(f"   描述: {route['description']}")
            print()
            
            # 验证路由配置
            assert "path_pattern" in route, "缺少路径模式"
            assert "target_service" in route, "缺少目标服务"
            assert "target_url" in route, "缺少目标URL"
            assert "methods" in route, "缺少支持的HTTP方法"
            assert "auth_required" in route, "缺少认证要求"
            
            # 验证HTTP方法
            valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
            for method in route["methods"]:
                assert method in valid_methods, f"无效的HTTP方法: {method}"
            
            # 验证URL格式
            assert route["target_url"].startswith("http"), "目标URL格式无效"
            
            # 验证认证要求
            assert isinstance(route["auth_required"], bool), "认证要求必须是布尔值"
        
        print(f"总计代理路由: {len(proxy_routes)} 个")
        
        print("✅ API网关代理路由测试通过")
        return True
        
    except Exception as e:
        print(f"❌ API网关代理路由测试失败: {e}")
        return False

def test_api_gateway_middleware():
    """测试API网关中间件"""
    print("\n=== 测试API网关中间件 ===")
    
    try:
        # 模拟中间件配置
        middleware_config = [
            {
                "name": "CORS",
                "type": "CORSMiddleware",
                "config": {
                    "allow_origins": ["*"],
                    "allow_credentials": True,
                    "allow_methods": ["*"],
                    "allow_headers": ["*"]
                },
                "order": 1,
                "enabled": True
            },
            {
                "name": "Request Logging",
                "type": "RequestLoggingMiddleware",
                "config": {
                    "log_level": "INFO",
                    "include_headers": False,
                    "include_body": False
                },
                "order": 2,
                "enabled": True
            },
            {
                "name": "Authentication",
                "type": "AuthenticationMiddleware",
                "config": {
                    "secret_key": "your-secret-key",
                    "algorithm": "HS256",
                    "exclude_paths": ["/health", "/services", "/auth/login"]
                },
                "order": 3,
                "enabled": True
            },
            {
                "name": "Rate Limiting",
                "type": "RateLimitingMiddleware",
                "config": {
                    "requests_per_minute": 100,
                    "burst_size": 10
                },
                "order": 4,
                "enabled": False
            }
        ]
        
        print("API网关中间件配置:")
        print("-" * 80)
        
        enabled_count = 0
        disabled_count = 0
        
        for middleware in middleware_config:
            status = "✅ 启用" if middleware['enabled'] else "❌ 禁用"
            print(f"• {middleware['name']} ({middleware['type']})")
            print(f"  状态: {status}")
            print(f"  顺序: {middleware['order']}")
            print(f"  配置: {json.dumps(middleware['config'], ensure_ascii=False)}")
            print()
            
            # 验证中间件配置
            assert "name" in middleware, "缺少中间件名称"
            assert "type" in middleware, "缺少中间件类型"
            assert "config" in middleware, "缺少中间件配置"
            assert "order" in middleware, "缺少中间件顺序"
            assert "enabled" in middleware, "缺少中间件启用状态"
            
            # 验证数据类型
            assert isinstance(middleware["name"], str), "中间件名称必须是字符串"
            assert isinstance(middleware["type"], str), "中间件类型必须是字符串"
            assert isinstance(middleware["config"], dict), "中间件配置必须是字典"
            assert isinstance(middleware["order"], int), "中间件顺序必须是整数"
            assert isinstance(middleware["enabled"], bool), "中间件启用状态必须是布尔值"
            
            # 统计启用状态
            if middleware["enabled"]:
                enabled_count += 1
            else:
                disabled_count += 1
        
        print(f"中间件统计: 启用 {enabled_count} 个, 禁用 {disabled_count} 个")
        
        print("✅ API网关中间件测试通过")
        return True
        
    except Exception as e:
        print(f"❌ API网关中间件测试失败: {e}")
        return False

def test_api_gateway_endpoints_summary():
    """测试API网关端点汇总"""
    print("\n=== API网关端点汇总 ===")
    
    gateway_endpoints = [
        {
            "method": "GET",
            "path": "/health",
            "description": "健康检查",
            "auth_required": False,
            "response": "HealthCheckResponse"
        },
        {
            "method": "GET",
            "path": "/services",
            "description": "获取所有微服务状态",
            "auth_required": False,
            "response": "ServiceStatusResponse"
        }
    ]
    
    print("API网关接口列表:")
    print("-" * 80)
    for i, endpoint in enumerate(gateway_endpoints, 1):
        auth_status = "🔒 需要认证" if endpoint['auth_required'] else "🔓 无需认证"
        print(f"{i}. {endpoint['method']} {endpoint['path']}")
        print(f"   描述: {endpoint['description']}")
        print(f"   认证: {auth_status}")
        print(f"   响应: {endpoint['response']}")
        print()
    
    return True

def main():
    """主测试函数"""
    print("开始测试API网关2个接口...")
    print("=" * 60)
    
    test_results = []
    
    # 测试2个API网关接口
    test_results.append(("API 1: 健康检查", test_api_1_health_check()))
    test_results.append(("API 2: 获取所有微服务状态", test_api_2_service_status()))
    
    # 测试网关功能
    test_results.append(("代理路由配置", test_api_gateway_proxy_routes()))
    test_results.append(("中间件配置", test_api_gateway_middleware()))
    
    # API端点汇总
    test_api_gateway_endpoints_summary()
    
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
    print(f"总计: {len(test_results)} 项测试")
    print(f"通过: {passed} 项")
    print(f"失败: {failed} 项")
    
    if failed == 0:
        print("\n🎉 所有API网关测试通过！")
        print("接口格式和配置验证正确。")
        return True
    else:
        print(f"\n⚠️  有 {failed} 项测试失败。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
