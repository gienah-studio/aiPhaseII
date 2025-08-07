from fastapi import FastAPI, Request, HTTPException, Depends
import httpx
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Dict, Any, Optional
from starlette.responses import JSONResponse, StreamingResponse, Response
import time
import jwt
from fastapi.security import OAuth2PasswordBearer
from httpx import AsyncClient
import copy

# 创建FastAPI应用
app = FastAPI(
    title="组织系统API",
    description="组织系统API文档",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置为特定的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 服务路由配置
SERVICE_ROUTES = {
    "auth": "http://auth_service:8000",
    "user": "http://user_service:8001",
    "organization": "http://organization_service:8002",
    "enterprise": "http://enterprise_service:8003",
    "permission": "http://permission_service:8004"
}

# OAuth2密码Bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# JWT密钥
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"

# 请求计数器
request_counter = 0

# 中间件：请求日志
@app.middleware("http")
async def log_requests(request: Request, call_next):
    global request_counter
    request_counter += 1
    request_id = request_counter
    
    # 记录请求开始
    start_time = time.time()
    path = request.url.path
    method = request.method
    print(f"[{request_id}] {method} {path} - 开始处理")
    
    # 处理请求
    try:
        response = await call_next(request)
        
        # 记录请求结束
        process_time = (time.time() - start_time) * 1000
        status_code = response.status_code
        print(f"[{request_id}] {method} {path} - 完成 {status_code} ({process_time:.2f}ms)")
        
        return response
    except Exception as e:
        # 记录请求异常
        process_time = (time.time() - start_time) * 1000
        print(f"[{request_id}] {method} {path} - 异常 {str(e)} ({process_time:.2f}ms)")
        
        return JSONResponse(
            status_code=500,
            content={"detail": "内部服务器错误"}
        )

# 验证令牌
async def verify_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    验证JWT令牌
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

# 路由：健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    """
    API网关健康检查
    """
    return {"status": "healthy", "timestamp": time.time()}

# 路由：服务状态
@app.get("/services", tags=["系统"])
async def service_status():
    """
    获取所有微服务的状态
    """
    async with httpx.AsyncClient() as client:
        results = {}
        for service_name, service_url in SERVICE_ROUTES.items():
            try:
                response = await client.get(f"{service_url}/health", timeout=2.0)
                if response.status_code == 200:
                    results[service_name] = {
                        "status": "up",
                        "url": service_url,
                        "details": response.json()
                    }
                else:
                    results[service_name] = {
                        "status": "error",
                        "url": service_url,
                        "details": {"status_code": response.status_code}
                    }
            except Exception as e:
                results[service_name] = {
                    "status": "down",
                    "url": service_url,
                    "details": {"error": str(e)}
                }
        
        return results

# 路由：代理请求到认证服务
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["认证服务"])
async def auth_proxy(path: str, request: Request):
    """
    代理请求到认证服务
    """
    return await proxy_request("auth", path, request)

# 路由：代理请求到用户服务
@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["用户服务"])
async def user_proxy(path: str, request: Request, token_data: Dict = Depends(verify_token)):
    """
    代理请求到用户服务
    """
    return await proxy_request("user", path, request, token_data)

# 路由：代理请求到组织服务
@app.api_route("/organizations/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["组织服务"])
async def organization_proxy(path: str, request: Request, token_data: Dict = Depends(verify_token)):
    """
    代理请求到组织服务
    """
    return await proxy_request("organization", path, request, token_data)

# 路由：代理请求到企业服务
@app.api_route("/enterprises/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["企业服务"])
async def enterprise_proxy(path: str, request: Request, token_data: Dict = Depends(verify_token)):
    """
    代理请求到企业服务
    """
    return await proxy_request("enterprise", path, request, token_data)

# 路由：代理请求到权限服务
@app.api_route("/permissions/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["权限服务"])
async def permission_proxy(path: str, request: Request, token_data: Dict = Depends(verify_token)):
    """
    代理请求到权限服务
    """
    return await proxy_request("permission", path, request, token_data)

# 代理请求函数
async def proxy_request(service: str, path: str, request: Request, token_data: Optional[Dict] = None):
    """
    代理请求到指定服务
    """
    if service not in SERVICE_ROUTES:
        raise HTTPException(status_code=404, detail=f"服务 {service} 不存在")
    
    # 构建目标URL
    target_url = f"{SERVICE_ROUTES[service]}/{path}"
    
    # 获取请求内容
    body = await request.body()
    headers = dict(request.headers)
    
    # 移除Host头，避免转发时的冲突
    if "host" in headers:
        del headers["host"]
    
    # 如果有令牌数据，添加到请求头中
    if token_data:
        headers["X-User-ID"] = str(token_data.get("sub", ""))
        headers["X-User-Role"] = str(token_data.get("role", ""))
    
    # 转发请求
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=request.query_params,
                content=body,
                timeout=30.0,
                follow_redirects=True
            )
            
            # 返回响应
            return StreamingResponse(
                content=response.aiter_bytes(),
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
        except httpx.RequestError as e:
            # 处理请求错误
            error_detail = f"服务 {service} 请求失败: {str(e)}"
            print(error_detail)
            raise HTTPException(status_code=503, detail=error_detail)

# 动态加载各服务的OpenAPI文档
@app.on_event("startup")
async def startup_event():
    """
    启动时加载所有服务的OpenAPI文档
    """
    combined_schema = {
        "openapi": "3.0.2",
        "info": {
            "title": "组织系统API",
            "description": "组织系统API文档",
            "version": "1.0.0"
        },
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {}
        }
    }
    
    async with httpx.AsyncClient() as client:
        for service_name, service_url in SERVICE_ROUTES.items():
            try:
                response = await client.get(f"{service_url}/openapi.json")
                if response.status_code == 200:
                    service_schema = response.json()
                    
                    # 合并paths
                    for path, path_item in service_schema.get("paths", {}).items():
                        # 添加服务名称前缀
                        new_path = f"/{service_name}{path}"
                        # 更新操作的tags
                        for operation in path_item.values():
                            if "tags" in operation:
                                operation["tags"] = [f"{service_name.capitalize()} - {tag}" 
                                                   for tag in operation["tags"]]
                            else:
                                operation["tags"] = [service_name.capitalize()]
                        combined_schema["paths"][new_path] = path_item
                    
                    # 合并components/schemas
                    if "components" in service_schema:
                        if "schemas" in service_schema["components"]:
                            for name, schema in service_schema["components"]["schemas"].items():
                                new_name = f"{service_name}_{name}"
                                combined_schema["components"]["schemas"][new_name] = schema
                                
                        # 合并securitySchemes
                        if "securitySchemes" in service_schema["components"]:
                            combined_schema["components"]["securitySchemes"].update(
                                service_schema["components"]["securitySchemes"]
                            )
                    
                print(f"Loaded OpenAPI schema for {service_name}")
            except Exception as e:
                print(f"Failed to load OpenAPI schema for {service_name}: {e}")
    
    # 添加系统级API的文档
    system_paths = {
        "/health": {
            "get": {
                "summary": "健康检查",
                "description": "API网关健康检查",
                "tags": ["System"],
                "responses": {
                    "200": {
                        "description": "健康状态",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "timestamp": {"type": "number"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/services": {
            "get": {
                "summary": "服务状态",
                "description": "获取所有微服务的状态",
                "tags": ["System"],
                "responses": {
                    "200": {
                        "description": "服务状态列表",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "url": {"type": "string"},
                                            "details": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    combined_schema["paths"].update(system_paths)
    app.openapi_schema = combined_schema
