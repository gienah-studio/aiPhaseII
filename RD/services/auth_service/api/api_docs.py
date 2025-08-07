from typing import Dict, Any

class AuthApiDocs:
    """认证相关API文档"""
    

    
    # 用户登录
    LOGIN = {
        "summary": "用户登录",
        "description": "用户登录并返回访问令牌",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "登录成功",
            "data": {
                "access_token": "访问令牌",
                "token_type": "令牌类型",
                "expires_in": "过期时间(秒)"
            }
        }
        ```
        """
    }
    

    

    

    
    # 获取个人信息
    GET_PROFILE = {
        "summary": "获取个人信息",
        "description": "获取当前登录用户的详细信息",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "获取成功",
            "data": {
                "id": "用户ID",
                "username": "用户名",
                "realName": "真实姓名",
                "phone": "手机号",
                "email": "邮箱",
                "enterpriseId": "企业ID",
                "enterpriseName": "企业名称",
                "enterpriseRegionCode": "企业所在地区编码",
                "enterpriseRegionName": "企业所在地区名称",
                "enterpriseAddress": "企业详细地址",
                "role": "角色",
                "status": "状态(0:待审核,1:正常,2:禁用)",
                "avatar": "头像URL",
                "createdAt": "创建时间",
                "updatedAt": "更新时间"
            }
        }
        ```
        """
    }
    
    # 上传文件
    UPLOAD_FILE = {
        "summary": "上传文件",
        "description": "上传文件并返回访问URL",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "上传成功",
            "data": {
                "url": "文件访问URL",
                "filename": "原始文件名",
                "content_type": "文件类型"
            }
        }
        ```
        """
    }
    
    # 修改密码（使用原密码）
    CHANGE_PASSWORD = {
        "summary": "修改密码",
        "description": "使用原密码修改为新密码",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "密码修改成功",
            "data": null
        }
        ```
        """
    }

    # 重置密码
    RESET_PASSWORD = {
        "summary": "重置密码",
        "description": "重置用户密码为123456",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "密码重置成功",
            "data": null
        }
        ```
        """
    }
    
    # 退出登录
    LOGOUT = {
        "summary": "退出登录",
        "description": "使当前用户登录的令牌失效",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "退出登录成功",
            "data": null
        }
        ```
        """
    }
    
    # 更新个人信息
    UPDATE_USER_INFO = {
        "summary": "更新个人信息",
        "description": "更新当前登录用户的个人信息（姓名、邮箱、头像），手机号作为登录账号不可修改",
        "response_description": """
        返回数据结构:
        ```json
        {
            "code": 200,
            "message": "更新成功",
            "data": {
                "id": "用户ID",
                "name": "用户姓名",
                "account": "账号",
                "phone": "手机号",
                "email": "邮箱",
                "avatar": "头像URL",
                "enterpriseId": "企业ID",
                "enterpriseName": "企业名称",
                "enterpriseRegionCode": "企业所在地区编码",
                "enterpriseRegionName": "企业所在地区名称",
                "enterpriseAddress": "企业详细地址",
                "departmentId": "部门ID",
                "departmentName": "部门名称",
                "userType": "用户类型",
                "status": "状态"
            }
        }
        ```
        """
    }
