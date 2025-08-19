# 专属客服列表模块

## 功能概述

专属客服列表模块提供了完整的虚拟客服管理功能，包括：

### 主要功能

1. **客服列表查看**
   - 分页显示客服列表
   - 支持按姓名、账号、等级搜索（前端本地过滤）
   - 显示客服基本信息：ID、姓名、账号、等级、手机号、身份证号、最后登录时间、创建时间

2. **客服管理**
   - 新增客服：创建新的虚拟客服账号（姓名、账号、初始密码）
   - 编辑客服：更新客服基本信息（仅姓名，账号不可修改）
   - 删除客服：软删除客服账号

3. **批量导入**
   - 支持 Excel (.xlsx) 和 CSV (.csv) 格式文件导入
   - 提供导入模板下载
   - 导入结果反馈，包括成功数量和失败详情

### API 接口

基于 `/src/api/ai二期.openapi.json` 中定义的接口：

- `GET /api/virtualOrders/customerService` - 获取客服列表
- `POST /api/virtualOrders/customerService` - 创建客服
- `PUT /api/virtualOrders/customerService/{cs_id}` - 更新客服信息
- `DELETE /api/virtualOrders/customerService/{cs_id}` - 删除客服
- `POST /api/virtualOrders/import/customerService` - 批量导入客服

### 数据结构

#### VirtualCustomerServiceInfo
```typescript
interface VirtualCustomerServiceInfo {
  id: number;
  user_id?: number;
  name: string;
  account: string;
  level: string;
  status: string;
  last_login_time?: string;
  created_at?: string;
}
```

#### 导入文件格式
CSV/Excel 文件应包含以下列：
- name: 客服姓名（必填）
- account: 客服账号（必填）

### 使用说明

1. **查看客服列表**：页面加载时自动获取客服列表
2. **搜索客服**：使用搜索框按条件筛选客服
3. **新增客服**：点击"新增客服"按钮，填写表单创建新客服
4. **编辑客服**：点击表格中的"编辑"按钮修改客服信息
5. **删除客服**：点击表格中的"删除"按钮删除客服（需确认）
6. **批量导入**：
   - 点击"下载模板"获取导入模板
   - 填写模板数据
   - 点击"批量导入"上传文件
   - 查看导入结果

### 注意事项

- 虚拟客服不需要手机号和身份证号信息
- 编辑时只能修改客服姓名，账号不可修改
- 导入文件大小限制为 10MB
- 删除操作为软删除，不会真正删除数据
- **API限制**：根据接口文档，GET请求只支持分页参数(page, size)，搜索功能通过前端本地过滤实现
- **业务调整**：虚拟客服简化为只包含姓名、账号和初始密码字段
