from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared.middlewares.case_middleware import CamelCaseMiddleware
from shared.middlewares.datetime_middleware import DatetimeMiddleware
from shared.middlewares.auth_middleware import AuthMiddleware

from fastapi.exceptions import RequestValidationError
from shared.exceptions import BusinessException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import os
import time
import asyncio
from contextlib import asynccontextmanager


# 设置时区为Asia/Shanghai
os.environ['TZ'] = 'Asia/Shanghai'
if hasattr(time, 'tzset'):
    time.tzset()

# 导入认证服务的路由
from services.auth_service.routers import auth # 认证服务
# 导入虚拟订单服务的路由
from services.virtual_order_service.routes import virtual_order_routes
from services.virtual_order_service.routes import bonus_pool_routes
# 导入资源库服务的路由
from services.resource_service.routes import resource_routes
# 导入定时任务调度器
from services.virtual_order_service.service.task_scheduler import start_background_tasks, stop_background_tasks

# 定义应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("初始化系统配置...")
    # 初始化自动确认配置
    from shared.database.session import SessionLocal
    from services.virtual_order_service.service.config_service import ConfigService

    db = SessionLocal()
    try:
        config_service = ConfigService(db)
        config_service.init_auto_confirm_config()
        config_service.init_virtual_task_generation_config()
    except Exception as e:
        print(f"初始化配置失败: {e}")
    finally:
        db.close()

    print("启动虚拟订单定时任务调度器...")
    # 在后台启动定时任务
    task = asyncio.create_task(start_background_tasks())
    try:
        yield
    finally:
        # 关闭时执行
        print("停止虚拟订单定时任务调度器...")
        stop_background_tasks()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="虚拟订单管理系统API",
    description="虚拟订单管理系统 - 包含认证服务和虚拟订单服务",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global exception handler caught: {str(exc)}")
    if isinstance(exc, BusinessException):
        return JSONResponse(
            status_code=200,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": exc.data
            }
        )
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": f"服务器内部错误: {str(exc)}",
            "data": None
        }
    )
class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException as exc:
            return JSONResponse(
                status_code=200,
                content={
                    "code": exc.status_code,
                    "message": exc.detail,
                    "data": None
                }
            )
        except BusinessException as exc:
            return JSONResponse(
                status_code=200,
                content={
                    "code": exc.code,
                    "message": exc.message,
                    "data": exc.data
                }
            )
        except Exception as exc:
            return JSONResponse(
                status_code=200,
                content={
                    "code": 500,
                    "message": str(exc),
                    "data": None
                }
            )

# 注册异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_messages = []
    for error in exc.errors():
        field = error.get("loc", [])[-1]
        msg = error.get("msg", "")
        error_messages.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=200,
        content={
            "code": 400,
            "message": "参数错误: " + "; ".join(error_messages),
            "data": None
        }
    )

# 添加异常处理中间件（最先执行）
app.add_middleware(ExceptionMiddleware)

# 添加认证中间件
app.add_middleware(AuthMiddleware)

# 添加自定义中间件
app.add_middleware(DatetimeMiddleware)
app.add_middleware(CamelCaseMiddleware)

# 配置CORS（放在最后，这样会最先处理预检请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册认证服务的路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证服务"])

# 注册虚拟订单服务的路由
app.include_router(virtual_order_routes.router, prefix="/api/virtualOrders", tags=["虚拟订单服务"])

# 注册奖金池管理路由
app.include_router(bonus_pool_routes.router, prefix="/api", tags=["奖金池管理"])

# 注册资源库管理路由
app.include_router(resource_routes.router, tags=["资源库管理"])

@app.get("/")
async def root():
    return {"message": "虚拟订单管理系统API - 认证服务和虚拟订单服务"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9007)