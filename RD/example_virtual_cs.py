#!/usr/bin/env python3
"""
虚拟客服管理示例脚本
演示如何创建、查询、更新和删除虚拟客服
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.database.session import SessionLocal
from services.virtual_order_service.service.virtual_order_service import VirtualOrderService

def create_sample_virtual_cs():
    """创建示例虚拟客服"""
    print("=== 创建示例虚拟客服 ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    try:
        # 创建多个虚拟客服
        cs_list = [
            {
                "name": "虚拟客服001",
                "account": "virtual_cs_001",
                "phone_number": "13800138001",
                "id_card": "110101199001011001"
            },
            {
                "name": "虚拟客服002", 
                "account": "virtual_cs_002",
                "phone_number": "13800138002",
                "id_card": "110101199001011002"
            },
            {
                "name": "虚拟客服003",
                "account": "virtual_cs_003",
                "phone_number": "13800138003",
                "id_card": "110101199001011003"
            }
        ]
        
        created_cs = []
        for cs_data in cs_list:
            try:
                result = service.create_virtual_customer_service(
                    name=cs_data["name"],
                    account=cs_data["account"],
                    phone_number=cs_data["phone_number"],
                    id_card=cs_data["id_card"],
                    initial_password="123456"
                )
                created_cs.append(result)
                print(f"✅ 创建成功: {cs_data['name']} (账号: {cs_data['account']})")
            except Exception as e:
                print(f"❌ 创建失败: {cs_data['name']} - {str(e)}")
        
        print(f"\n成功创建 {len(created_cs)} 个虚拟客服")
        return created_cs
        
    except Exception as e:
        print(f"创建虚拟客服失败: {str(e)}")
        return []
    finally:
        db.close()

def list_virtual_cs():
    """查询虚拟客服列表"""
    print("\n=== 查询虚拟客服列表 ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    try:
        result = service.get_virtual_customer_services(page=1, size=20)
        
        print(f"虚拟客服总数: {result['total']}")
        print(f"当前页: {result['page']}, 每页: {result['size']}")
        print("\n虚拟客服列表:")
        print("-" * 80)
        print(f"{'ID':<5} {'姓名':<15} {'账号':<20} {'手机号':<15} {'级别':<5}")
        print("-" * 80)
        
        for cs in result['items']:
            print(f"{cs['role_id']:<5} {cs['name']:<15} {cs['account']:<20} {cs['phone_number'] or 'N/A':<15} {cs['level']:<5}")
        
        return result['items']
        
    except Exception as e:
        print(f"查询虚拟客服列表失败: {str(e)}")
        return []
    finally:
        db.close()

def update_virtual_cs_example(role_id: int):
    """更新虚拟客服示例"""
    print(f"\n=== 更新虚拟客服 (ID: {role_id}) ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    try:
        # 更新客服信息
        update_data = {
            "name": f"更新后的客服_{role_id}",
            "phone_number": "13900139000"
        }
        
        result = service.update_virtual_customer_service(role_id, update_data)
        
        print(f"✅ 更新成功:")
        print(f"   角色ID: {result['role_id']}")
        print(f"   姓名: {result['name']}")
        print(f"   账号: {result['account']}")
        print(f"   更新字段: {', '.join(result['updated_fields'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新虚拟客服失败: {str(e)}")
        return False
    finally:
        db.close()

def delete_virtual_cs_example(role_id: int):
    """删除虚拟客服示例"""
    print(f"\n=== 删除虚拟客服 (ID: {role_id}) ===")
    
    db = SessionLocal()
    service = VirtualOrderService(db)
    
    try:
        result = service.delete_virtual_customer_service(role_id)
        
        print(f"✅ 删除成功:")
        print(f"   角色ID: {result['role_id']}")
        print(f"   姓名: {result['name']}")
        print(f"   账号: {result['account']}")
        print(f"   已删除: {result['deleted']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 删除虚拟客服失败: {str(e)}")
        return False
    finally:
        db.close()

def main():
    """主函数"""
    print("虚拟客服管理示例")
    print("=" * 50)
    
    try:
        # 1. 创建示例虚拟客服
        created_cs = create_sample_virtual_cs()
        
        # 2. 查询虚拟客服列表
        cs_list = list_virtual_cs()
        
        if cs_list:
            # 3. 更新第一个虚拟客服
            first_cs = cs_list[0]
            update_virtual_cs_example(first_cs['role_id'])
            
            # 4. 再次查询列表查看更新结果
            print("\n=== 更新后的虚拟客服列表 ===")
            list_virtual_cs()
            
            # 5. 删除最后一个虚拟客服（如果有多个）
            if len(cs_list) > 1:
                last_cs = cs_list[-1]
                delete_virtual_cs_example(last_cs['role_id'])
                
                # 6. 最终查询列表
                print("\n=== 删除后的虚拟客服列表 ===")
                list_virtual_cs()
        
        print("\n" + "=" * 50)
        print("虚拟客服管理示例完成！")
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
