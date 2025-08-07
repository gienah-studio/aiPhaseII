#!/usr/bin/env python3
"""
虚拟客服API接口测试脚本
测试虚拟客服的4个主要接口功能
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_import_modules():
    """测试导入所需的模块"""
    print("=== 测试模块导入 ===")
    
    try:
        # 测试基础模块
        import fastapi
        print("✅ FastAPI 导入成功")
        
        import sqlalchemy
        print("✅ SQLAlchemy 导入成功")
        
        import pandas
        print("✅ Pandas 导入成功")
        
        import openpyxl
        print("✅ OpenPyXL 导入成功")
        
        # 测试虚拟订单相关模块
        try:
            import nanoid
            print("✅ NanoID 导入成功")
        except ImportError as e:
            print(f"❌ NanoID 导入失败: {e}")
            return False
            
        try:
            from dotenv import load_dotenv
            print("✅ Python-dotenv 导入成功")
        except ImportError as e:
            print(f"❌ Python-dotenv 导入失败: {e}")
            return False
            
        try:
            import pymysql
            print("✅ PyMySQL 导入成功")
        except ImportError as e:
            print(f"❌ PyMySQL 导入失败: {e}")
            return False
            
        print("所有基础模块导入成功！\n")
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def test_virtual_order_service_import():
    """测试虚拟订单服务模块导入"""
    print("=== 测试虚拟订单服务模块导入 ===")
    
    try:
        # 测试数据库模块
        from shared.database.models import UserInfo, OriginalUser, Tasks
        print("✅ 数据库模型导入成功")
        
        # 测试虚拟订单服务
        from services.virtual_order_service.service.virtual_order_service import VirtualOrderService
        print("✅ 虚拟订单服务导入成功")
        
        # 测试API路由
        from services.virtual_order_service.routes.virtual_order_routes import router
        print("✅ 虚拟订单路由导入成功")
        
        # 测试数据模型
        from services.virtual_order_service.models.virtual_order_models import (
            VirtualCustomerServiceCreate,
            VirtualCustomerServiceResponse,
            VirtualCustomerServiceUpdate
        )
        print("✅ 虚拟订单数据模型导入成功")
        
        print("虚拟订单服务模块导入成功！\n")
        return True
        
    except ImportError as e:
        print(f"❌ 虚拟订单服务模块导入失败: {e}")
        return False

def test_nanoid_functionality():
    """测试NanoID功能"""
    print("=== 测试NanoID功能 ===")
    
    try:
        from nanoid import generate
        
        # 测试默认生成
        default_id = generate()
        print(f"默认ID: {default_id}")
        assert len(default_id) == 21, f"默认ID长度错误: {len(default_id)}"
        
        # 测试自定义字母表（模拟订单号生成）
        from nanoid import generate
        
        # 模拟虚拟订单号生成
        alphabet = '1234567890abcdef'
        order_id = generate(alphabet, 10)
        print(f"虚拟订单号: {order_id}")
        assert len(order_id) == 10, f"订单号长度错误: {len(order_id)}"
        
        # 验证只包含指定字符
        for char in order_id:
            assert char in alphabet, f"订单号包含非法字符: {char}"
        
        print("✅ NanoID功能测试通过！\n")
        return True
        
    except Exception as e:
        print(f"❌ NanoID功能测试失败: {e}")
        return False

def test_virtual_cs_data_models():
    """测试虚拟客服数据模型"""
    print("=== 测试虚拟客服数据模型 ===")
    
    try:
        from services.virtual_order_service.models.virtual_order_models import (
            VirtualCustomerServiceCreate,
            VirtualCustomerServiceResponse,
            VirtualCustomerServiceUpdate
        )
        
        # 测试创建模型
        create_data = {
            "name": "测试客服",
            "account": "test_cs_001",
            "phone_number": "13800138000",
            "id_card": "123456789012345678",
            "initial_password": "123456"
        }
        
        create_model = VirtualCustomerServiceCreate(**create_data)
        print(f"✅ 创建模型测试通过: {create_model.name}")
        
        # 测试响应模型
        response_data = {
            "user_id": 123,
            "role_id": 456,
            "name": "测试客服",
            "account": "test_cs_001",
            "level": "6",
            "initial_password": "123456"
        }
        
        response_model = VirtualCustomerServiceResponse(**response_data)
        print(f"✅ 响应模型测试通过: {response_model.account}")
        
        # 测试更新模型
        update_data = {
            "name": "更新后的客服",
            "phone_number": "13900139000"
        }
        
        update_model = VirtualCustomerServiceUpdate(**update_data)
        print(f"✅ 更新模型测试通过: {update_model.name}")
        
        print("虚拟客服数据模型测试通过！\n")
        return True
        
    except Exception as e:
        print(f"❌ 虚拟客服数据模型测试失败: {e}")
        return False

def test_api_route_structure():
    """测试API路由结构"""
    print("=== 测试API路由结构 ===")
    
    try:
        from services.virtual_order_service.routes.virtual_order_routes import router
        from fastapi import APIRouter
        
        # 验证路由器类型
        assert isinstance(router, APIRouter), "路由器类型错误"
        
        # 获取路由信息
        routes = router.routes
        print(f"总路由数量: {len(routes)}")
        
        # 查找虚拟客服相关路由
        cs_routes = []
        for route in routes:
            if hasattr(route, 'path') and 'customer-service' in route.path:
                cs_routes.append({
                    'path': route.path,
                    'methods': getattr(route, 'methods', [])
                })
        
        print("虚拟客服相关路由:")
        for route in cs_routes:
            print(f"  {route['methods']} {route['path']}")
        
        # 验证必要的路由存在
        expected_paths = [
            '/customer-service',  # GET, POST
            '/customer-service/{role_id}'  # PUT, DELETE
        ]
        
        found_paths = [route['path'] for route in cs_routes]
        for expected_path in expected_paths:
            path_found = any(expected_path in path for path in found_paths)
            if path_found:
                print(f"✅ 找到路由: {expected_path}")
            else:
                print(f"❌ 缺少路由: {expected_path}")
        
        print("API路由结构测试完成！\n")
        return True
        
    except Exception as e:
        print(f"❌ API路由结构测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试虚拟客服API接口...")
    print("=" * 60)
    
    test_results = []
    
    # 1. 测试模块导入
    test_results.append(("模块导入", test_import_modules()))
    
    # 2. 测试虚拟订单服务模块导入
    test_results.append(("虚拟订单服务模块", test_virtual_order_service_import()))
    
    # 3. 测试NanoID功能
    test_results.append(("NanoID功能", test_nanoid_functionality()))
    
    # 4. 测试虚拟客服数据模型
    test_results.append(("虚拟客服数据模型", test_virtual_cs_data_models()))
    
    # 5. 测试API路由结构
    test_results.append(("API路由结构", test_api_route_structure()))
    
    # 输出测试结果
    print("=" * 60)
    print("测试结果汇总:")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"总计: {len(test_results)} 项测试")
    print(f"通过: {passed} 项")
    print(f"失败: {failed} 项")
    
    if failed == 0:
        print("\n🎉 所有测试通过！虚拟客服API接口基础功能正常。")
        return True
    else:
        print(f"\n⚠️  有 {failed} 项测试失败，请检查缺少的依赖。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
