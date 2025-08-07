from sqlalchemy.orm import Session
from shared.database.session import get_db
from shared.models import Module, Operation, ModuleOperation

def init_module_operations():
    """初始化模块操作权限配置"""
    try:
        db = next(get_db())
        
        # 定义模块的操作权限配置
        module_operations = {
            # 通讯录
            "address_book": ["view", "add", "edit", "delete"],
            # 角色管理
            "role_management": ["view", "add", "edit", "delete"],
            # 企业信息
            "enterprise_info": ["view", "edit"],
            # 企业审批
            "enterprise_audit": ["view", "add", "edit", "delete"],
            # 管理员管理
            "admin_management": ["view", "add", "edit", "delete"],
            # 权限组管理
            "permission_group": ["view", "add", "edit", "delete"],
            # 操作日志
            "operation_log": ["view", "export"],
            # 粮食价格管理
            "grain-price": ["view", "add", "edit", "delete", "price_report"]
        }
        
        # 获取所有菜单类型的模块
        modules = db.query(Module).filter(Module.type == 1).all()
        
        # 获取所有操作
        operations = {op.code: op for op in db.query(Operation).all()}
        
        # 检查并更新每个模块的操作权限
        for module in modules:
            if module.code in module_operations:
                # 获取该模块应该有的操作权限
                operation_codes = module_operations[module.code]
                
                # 获取模块当前的操作权限
                existing_operations = db.query(ModuleOperation).filter(
                    ModuleOperation.module_id == module.id
                ).all()
                existing_operation_ids = {op.operation_id for op in existing_operations}
                
                # 添加缺少的操作权限
                for code in operation_codes:
                    if code in operations:
                        operation_id = operations[code].id
                        if operation_id not in existing_operation_ids:
                            module_operation = ModuleOperation(
                                module_id=module.id,
                                operation_id=operation_id
                            )
                            db.add(module_operation)
                
                # 删除多余的操作权限
                valid_operation_ids = {operations[code].id for code in operation_codes if code in operations}
                for existing_op in existing_operations:
                    if existing_op.operation_id not in valid_operation_ids:
                        db.delete(existing_op)
        
        db.commit()
        print("模块操作权限配置初始化成功")
        
    except Exception as e:
        db.rollback()
        print(f"模块操作权限配置初始化失败: {str(e)}")
        raise e

if __name__ == "__main__":
    init_module_operations()