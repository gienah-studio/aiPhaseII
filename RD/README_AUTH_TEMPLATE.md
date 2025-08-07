# 认证服务模板

这是一个基于FastAPI的用户注册和登录认证服务模板，已经简化为只包含核心认证功能。

## 功能特性

- ✅ 用户注册（手机号+验证码）
- ✅ 用户登录（账号密码/手机号验证码）
- ✅ 密码重置
- ✅ JWT Token认证
- ✅ 用户信息管理
- ✅ 登录日志记录
- ✅ Redis验证码存储
- ✅ 密码加密存储

## 技术栈

- **Web框架**: FastAPI
- **数据库**: MySQL + SQLAlchemy
- **认证**: JWT + bcrypt
- **缓存**: Redis
- **数据验证**: Pydantic
- **数据库迁移**: Alembic

## 项目结构

```
api-platform/
├── main.py                 # 主应用入口
├── services/
│   └── auth_service/       # 认证服务
│       ├── routers/        # 路由定义
│       ├── service/        # 业务逻辑
│       └── schemas/        # 数据模型
├── shared/                 # 共享组件
│   ├── models/            # 数据库模型
│   ├── utils/             # 工具函数
│   ├── middlewares/       # 中间件
│   └── dependencies/      # 依赖注入
└── requirements_auth_template.txt  # 简化的依赖文件
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements_auth_template.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/dbname

# JWT配置
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# 短信服务配置（可选）
ALIYUN_ACCESS_KEY_ID=your-access-key
ALIYUN_ACCESS_KEY_SECRET=your-secret
```

### 3. 数据库迁移

```bash
alembic upgrade head
```

### 4. 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API接口

### 认证相关

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 账号密码登录
- `POST /api/auth/phoneLogin` - 手机号验证码登录
- `POST /api/auth/sendVerificationCode` - 发送验证码
- `POST /api/auth/resetPassword` - 重置密码
- `GET /api/auth/profile` - 获取用户信息
- `PUT /api/auth/updateUserInfo` - 更新用户信息
- `POST /api/auth/changePassword` - 修改密码
- `POST /api/auth/logout` - 退出登录

### 接口文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 核心模型

### User 用户模型

```python
class User(Base, BaseModel):
    name: str                    # 用户姓名
    account: str                 # 账号
    password: str                # 密码（加密）
    phone: str                   # 手机号
    email: str                   # 邮箱
    avatar: str                  # 头像
    enterprise_name: str         # 企业名称
    status: int                  # 状态(0:待审核,1:启用,2:禁用)
    user_type: int              # 用户类型(0:员工,1:管理员,2:超级管理员)
    auditor_id: int             # 审核人ID
```

## 扩展建议

基于此模板，您可以根据业务需求添加以下功能：

1. **权限管理**: 角色权限系统
2. **组织架构**: 部门、职位管理
3. **企业管理**: 多租户支持
4. **文件上传**: OSS/本地文件存储
5. **操作日志**: 用户行为记录
6. **通知系统**: 消息推送
7. **数据导出**: Excel/PDF导出
8. **API限流**: 接口访问控制

## 注意事项

1. 请确保在生产环境中使用强密码作为JWT密钥
2. 建议配置HTTPS以保护数据传输安全
3. 定期备份数据库数据
4. 监控Redis内存使用情况
5. 根据实际需求调整Token过期时间

## 许可证

MIT License
