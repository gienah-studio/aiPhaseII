# 虚拟订单管理系统

## 系统概述

虚拟订单管理系统是一个独立的订单生成和管理系统，与现有的nest项目共享数据库。主要功能包括：

1. **学生补贴管理** - 导入学生补贴信息，自动生成虚拟任务
2. **专用客服管理** - 导入和管理虚拟订单专用客服
3. **虚拟任务生成** - 按照5的倍数智能分配任务金额
4. **过期任务处理** - 自动处理24小时过期的未接取任务
5. **统计报表** - 生成虚拟订单统计报表

## 技术架构

- **后端框架**: FastAPI
- **数据库**: MySQL (与nest项目共享)
- **ORM**: SQLAlchemy
- **ID生成**: nanoid (与nest项目保持一致)
- **文件处理**: pandas + openpyxl

## 数据库表结构

### 新增表

1. **virtual_order_pool** - 虚拟订单资金池
2. **virtual_order_reports** - 虚拟订单统计报表

### 修改表

1. **tasks** - 新增 `is_virtual` 字段标识虚拟任务

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

新增的依赖包括：
- nanoid==2.0.0
- pandas>=1.5.0
- openpyxl>=3.0.0

### 2. 数据库迁移

执行SQL脚本创建新表：
```sql
-- 执行 notes/sql.sql 中的虚拟订单相关表结构
```

### 3. 启动服务

```bash
python main.py
```

服务将在 http://localhost:9007 启动

## API接口

### 基础路径
所有虚拟订单API的基础路径为：`/api/virtual-orders`

### 主要接口

#### 1. 导入学生补贴表
```
POST /api/virtual-orders/import/student-subsidy
Content-Type: multipart/form-data

参数：
- file: Excel文件

Excel格式要求：
- 必需列：学生姓名、补贴金额
- 可选列：其他学生信息
```

#### 2. 导入专用客服
```
POST /api/virtual-orders/import/customer-service
Content-Type: multipart/form-data

参数：
- file: Excel文件

Excel格式要求：
- 必需列：姓名、账号
- 可选列：手机号、身份证号
```

#### 3. 获取虚拟订单统计
```
GET /api/virtual-orders/stats

返回：
- 总学生数
- 总补贴金额
- 生成任务数
- 完成任务数
- 完成率
```

#### 4. 获取学生补贴池列表
```
GET /api/virtual-orders/student-pools?page=1&size=20&status=active

参数：
- page: 页码
- size: 每页数量
- status: 状态过滤 (active/completed/expired)
```

#### 5. 重新分配学生任务
```
POST /api/virtual-orders/reallocate/{student_id}

功能：手动触发学生剩余金额的任务重新分配
```

#### 6. 学生收入管理

**导出学生收入数据**
```
GET /api/virtual-orders/student-income/export

参数：无需任何参数

返回：Excel文件下载
- 导出所有学生的收入数据，有多少导出多少
- 包含学生收入统计工作表
- 包含使用说明工作表
- 补贴金额列供用户填写
```

**获取学生收入汇总**
```
GET /api/virtual-orders/student-income/summary?start_date=2023-01-01&end_date=2023-12-31

返回：
- 学生总数
- 任务总数和总金额
- 完成任务数和完成金额
- 完成率统计
```

#### 7. 虚拟客服管理

**创建虚拟客服**
```
POST /api/virtual-orders/customer-service
Content-Type: application/json

{
    "name": "客服姓名",
    "account": "客服账号",
    "phone_number": "手机号",
    "id_card": "身份证号",
    "initial_password": "初始密码"
}
```

**获取虚拟客服列表**
```
GET /api/virtual-orders/customer-service?page=1&size=20

返回：虚拟客服列表（level=6）
```

**更新虚拟客服信息**
```
PUT /api/virtual-orders/customer-service/{role_id}
Content-Type: application/json

{
    "name": "新姓名",
    "phone_number": "新手机号",
    "id_card": "新身份证号"
}
```

**删除虚拟客服**
```
DELETE /api/virtual-orders/customer-service/{role_id}

功能：软删除虚拟客服账号
```

## 业务逻辑

### 虚拟任务生成规则

1. **金额分配**
   - 基础单位：5元
   - 随机生成5的倍数：5、10、15、20、25...
   - 总金额 = 所有任务金额之和
   - 不能被5整除的余数作为单独任务

2. **任务属性**
   - `is_virtual`: true
   - `source`: 固定值（淘宝/集团业务/其他业务）
   - `order_number`: nanoid生成（10位，字符集：1234567890abcdef）
   - `end_date`: 创建时间 + 1天
   - `delivery_date`: 创建时间 + 3天

### 过期处理机制

1. **检查频率**: 每小时检查一次
2. **过期标准**: 创建24小时后未接取
3. **处理流程**:
   - 删除过期任务
   - 金额返还到补贴池
   - 重新生成新的任务组合

## 测试

### 运行基础功能测试
```bash
python test_virtual_order.py
```

测试内容包括：
- 金额分配算法
- 订单号生成
- 虚拟任务创建
- 批量任务生成

### API测试

启动服务后访问：http://localhost:9007/docs

使用Swagger UI进行API测试

## 配置说明

### 任务模板配置

在 `services/virtual_order_service/service/virtual_order_service.py` 中的 `task_templates` 配置：

```python
self.task_templates = {
    'summary': '虚拟任务 - 数据处理',
    'requirement': '请按照要求完成数据处理任务...',
    'source': '集团业务',  # 可选：淘宝、集团业务、其他业务
    'commission_unit': '元',
    'end_date_days': 1,  # 接单截止时间：创建后1天
    'delivery_date_days': 3,  # 交稿时间：接单后3天
}
```

### 专用客服级别配置

在 `UserInfo` 表中，专用客服的 `level` 字段值为 `'6'`

**级别说明：**
- 0: 管理员
- 1: 一级代理
- 2: 二级代理
- 3: 学员
- 4: 企业代理
- 5: 个人代理
- 6: 虚拟订单专用客服
- -1: 商业贷款
- -2: 个体工商户

### 虚拟客服管理

**创建流程：**
1. 创建 `OriginalUser` 记录（用户账号）
2. 创建 `UserInfo` 记录（用户信息，level=6）
3. 设置初始密码（默认123456）
4. 角色设置为 `virtual_customer_service`

**权限特点：**
- 专门服务虚拟订单
- 与普通客服区分管理
- 支持批量导入和单个创建
- 支持信息更新和软删除

## 监控和日志

### 日志位置
- 应用日志：控制台输出
- 定时任务日志：包含过期任务处理详情

### 监控指标
- 虚拟任务生成数量
- 任务完成率
- 过期任务处理情况
- 补贴池状态

## 注意事项

1. **数据一致性**: 与nest系统共享数据库，注意数据同步
2. **性能考虑**: 大量任务生成时注意数据库性能
3. **安全性**: Excel导入需要验证文件内容和大小
4. **备份**: 定期备份虚拟订单相关数据

## 故障排除

### 常见问题

1. **导入失败**
   - 检查Excel文件格式
   - 验证必需列是否存在
   - 查看错误日志

2. **任务生成失败**
   - 检查学生信息是否存在
   - 验证补贴金额格式
   - 查看数据库连接

3. **过期任务处理异常**
   - 检查定时任务日志
   - 验证数据库事务
   - 重启定时任务服务

## 后续扩展

1. **报表功能** - 完善Excel报表生成
2. **通知功能** - 任务状态变更通知
3. **审批流程** - 补贴金额审批机制
4. **API对接** - 与nest系统的实时数据同步
