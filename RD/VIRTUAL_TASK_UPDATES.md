# 虚拟任务配置更新说明

## 更新内容

### 1. 任务配置修改

已修改虚拟任务的以下配置：

- **task_level**: 从 "初级" 改为 "D"
- **status**: 从 "待接取" 改为 "0" 
- **commission_unit**: 从 "元" 改为 "人民币"

### 2. 数据库字段添加

为 `tasks` 表添加了新字段 `target_student_id`：

```sql
-- 执行以下SQL来添加字段
ALTER TABLE `tasks` 
ADD COLUMN `target_student_id` int DEFAULT NULL COMMENT '目标学生ID，虚拟任务专用，限制只有指定学生可以接取' 
AFTER `is_virtual`;

-- 添加索引以提高查询性能
ALTER TABLE `tasks` 
ADD INDEX `idx_target_student_id` (`target_student_id`);

-- 添加复合索引，用于快速查询某个学生的虚拟任务
ALTER TABLE `tasks` 
ADD INDEX `idx_virtual_target_student` (`is_virtual`, `target_student_id`);
```

### 3. 功能说明

#### target_student_id 字段的作用：
- **限制访问**: 虚拟任务只能被指定的学生看到和接取
- **不影响普通任务**: 该字段对普通任务为 NULL，不影响现有系统流程
- **精确匹配**: 只有 target_student_id 与学生ID匹配的虚拟任务才对该学生可见

#### 状态码说明：
- **"0"**: 待接取状态（虚拟任务专用）
- 与现有系统的状态管理保持兼容

### 4. 代码修改文件

以下文件已更新：

1. **RD/shared/models/tasks.py**
   - 添加 `target_student_id` 字段定义

2. **RD/services/virtual_order_service/service/virtual_order_service.py**
   - 更新任务模板配置
   - 在创建虚拟任务时设置 `target_student_id`
   - 更新重新分配任务的查询条件

3. **RD/services/virtual_order_service/service/task_scheduler.py**
   - 更新过期任务检查的状态条件
   - 使用 `target_student_id` 关联学生

### 5. 兼容性保证

- **向后兼容**: 新字段对现有普通任务无影响
- **数据完整性**: 所有现有数据保持不变
- **系统稳定性**: 不影响现有的任务流程和业务逻辑

### 6. 使用方式

虚拟任务创建后：
- 只有 `target_student_id` 指定的学生能看到该任务
- 其他学生无法看到或接取该虚拟任务
- 普通任务的显示和接取逻辑保持不变

### 7. 注意事项

1. **必须先执行SQL**: 在使用新功能前，请先执行 `add_target_student_id_field.sql` 中的SQL语句
2. **数据库备份**: 建议在执行SQL前备份数据库
3. **测试验证**: 建议在测试环境先验证功能正常后再部署到生产环境

## 文件清单

- `RD/scripts/add_target_student_id_field.sql` - 数据库字段添加脚本
- `RD/VIRTUAL_TASK_UPDATES.md` - 本说明文档
