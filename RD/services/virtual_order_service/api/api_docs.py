class VirtualOrderApiDocs:
    """虚拟订单相关API文档"""

    # 导入学生补贴表
    IMPORT_STUDENT_SUBSIDY = {
        "summary": "导入学生补贴表",
        "description": "上传Excel文件，导入学生补贴信息并自动生成虚拟任务",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "导入成功",
            "data": {
                "import_batch": "批次号",
                "total_students": 10,
                "total_subsidy": 2000.00,
                "generated_tasks": 45
            }
        }
        ```
        """
    }

    # 导入专用客服
    IMPORT_CUSTOMER_SERVICE = {
        "summary": "导入专用客服",
        "description": "上传Excel文件，导入专用客服信息",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "导入成功",
            "data": {
                "total_imported": 5,
                "failed_count": 0
            }
        }
        ```
        """
    }

    # 获取虚拟订单统计
    GET_VIRTUAL_ORDER_STATS = {
        "summary": "获取虚拟订单统计",
        "description": "获取虚拟订单的统计信息",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "获取成功",
            "data": {
                "total_students": 100,
                "total_subsidy": 20000.00,
                "total_tasks_generated": 450,
                "total_tasks_completed": 320,
                "completion_rate": 71.11
            }
        }
        ```
        """
    }

    # 获取虚拟订单当天统计
    GET_VIRTUAL_ORDER_DAILY_STATS = {
        "summary": "获取虚拟订单当天统计",
        "description": "获取虚拟订单当天的生成任务数量、完成任务数量、补贴金额、完成率、活跃学生人数",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "获取成功",
            "data": {
                "date": "2024-01-15",
                "daily_tasks_generated": 25,
                "daily_tasks_completed": 18,
                "daily_subsidy": 1800.00,
                "daily_active_students": 15,
                "daily_completion_rate": 72.00
            }
        }
        ```
        """
    }

    # 获取学生补贴池列表
    GET_STUDENT_POOLS = {
        "summary": "获取学生补贴池列表",
        "description": "分页获取学生补贴池信息",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "获取成功",
            "data": {
                "items": [...],
                "total": 100,
                "page": 1,
                "size": 20
            }
        }
        ```
        """
    }

    # 重新分配学生任务
    REALLOCATE_STUDENT_TASKS = {
        "summary": "重新分配学生任务",
        "description": "手动触发学生剩余金额的任务重新分配",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "重新分配成功",
            "data": {
                "student_id": 123,
                "remaining_amount": 150.00,
                "new_tasks_count": 8
            }
        }
        ```
        """
    }

    # 生成虚拟订单报表
    GENERATE_REPORT = {
        "summary": "生成虚拟订单报表",
        "description": "生成指定日期范围的虚拟订单统计报表",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "报表生成成功",
            "data": {
                "report_url": "/downloads/virtual_order_report_20231201.xlsx",
                "total_records": 100
            }
        }
        ```
        """
    }

    # 创建虚拟客服
    CREATE_VIRTUAL_CUSTOMER_SERVICE = {
        "summary": "创建虚拟客服",
        "description": "创建虚拟订单专用客服账号",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "创建成功",
            "data": {
                "id": 123,
                "user_id": 456,
                "name": "客服姓名",
                "account": "客服账号",
                "level": "6",
                "status": "active",
                "initial_password": "123456"
            }
        }
        ```
        """
    }

    # 获取虚拟客服列表
    GET_VIRTUAL_CUSTOMER_SERVICES = {
        "summary": "获取虚拟客服列表",
        "description": "分页获取虚拟订单专用客服列表",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "获取成功",
            "data": {
                "items": [...],
                "total": 10,
                "page": 1,
                "size": 20
            }
        }
        ```
        """
    }

    # 更新虚拟客服
    UPDATE_VIRTUAL_CUSTOMER_SERVICE = {
        "summary": "更新虚拟客服信息",
        "description": "更新虚拟订单专用客服的基本信息",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "更新成功",
            "data": {
                "id": 456,
                "name": "新姓名",
                "account": "客服账号",
                "status": "active",
                "updated_fields": ["name", "status"]
            }
        }
        ```
        """
    }

    # 删除虚拟客服
    DELETE_VIRTUAL_CUSTOMER_SERVICE = {
        "summary": "删除虚拟客服",
        "description": "删除虚拟订单专用客服（软删除）",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "删除成功",
            "data": {
                "id": 456,
                "name": "客服姓名",
                "account": "客服账号",
                "deleted": true
            }
        }
        ```
        """
    }

    # 导出学生收入数据
    EXPORT_STUDENT_INCOME = {
        "summary": "导出学生收入数据",
        "description": "导出所有学生收入统计数据为Excel文件，无需任何参数，有多少导出多少",
        "response_description": """
        返回Excel文件下载:
        - Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
        - 包含学生收入统计和使用说明两个工作表
        - 导出所有学生的收入数据，无日期和学生ID限制
        - 补贴金额列供用户填写后重新导入
        """
    }

    # 获取学生收入汇总
    GET_STUDENT_INCOME_SUMMARY = {
        "summary": "获取学生收入汇总",
        "description": "获取学生收入的汇总统计信息",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "获取成功",
            "data": {
                "total_students": 100,
                "total_tasks": 500,
                "total_amount": 25000.00,
                "completed_tasks": 450,
                "completed_amount": 22500.00,
                "completion_rate": 90.0,
                "export_time": "2023-12-01 10:30:00"
            }
        }
        ```
        """
    }
