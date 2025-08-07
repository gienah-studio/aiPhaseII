-- 用户表结构修复迁移脚本
-- 将现有的user表结构修改为与SQL设计一致

-- 1. 重命名表名：user -> users
ALTER TABLE `user` RENAME TO `users`;

-- 2. 添加新字段
ALTER TABLE `users` ADD COLUMN `enterprise_id` BIGINT UNSIGNED NULL COMMENT '所属企业ID, NULL表示个体用户' AFTER `id`;
ALTER TABLE `users` ADD COLUMN `role` ENUM('admin', 'provider', 'consumer') NOT NULL DEFAULT 'consumer' COMMENT '平台核心角色' AFTER `avatar`;
ALTER TABLE `users` ADD COLUMN `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注' AFTER `role`;

-- 3. 修改字段属性
-- name字段改为可空
ALTER TABLE `users` MODIFY COLUMN `name` VARCHAR(50) DEFAULT NULL COMMENT '用户真实姓名';

-- password字段长度改为255
ALTER TABLE `users` MODIFY COLUMN `password` VARCHAR(255) NOT NULL COMMENT '加密后的密码';

-- status字段改为ENUM类型
ALTER TABLE `users` MODIFY COLUMN `status` ENUM('pending_approval', 'active', 'rejected', 'suspended') NOT NULL DEFAULT 'pending_approval' COMMENT '账户状态';

-- email字段添加唯一约束
ALTER TABLE `users` ADD UNIQUE KEY `uk_email` (`email`);

-- 4. 删除不需要的字段
ALTER TABLE `users` DROP COLUMN `enterprise_name`;
ALTER TABLE `users` DROP COLUMN `user_type`;
ALTER TABLE `users` DROP COLUMN `auditor_id`;

-- 5. 添加索引
ALTER TABLE `users` ADD KEY `idx_enterprise_id` (`enterprise_id`);

-- 6. 添加外键约束（如果enterprises表存在）
-- 注意：只有在enterprises表存在时才执行此语句
-- ALTER TABLE `users` ADD CONSTRAINT `fk_users_enterprise_id` FOREIGN KEY (`enterprise_id`) REFERENCES `enterprises` (`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- 7. 更新现有数据
-- 将所有现有用户的enterprise_id设为NULL（个体用户）
UPDATE `users` SET `enterprise_id` = NULL WHERE `enterprise_id` IS NOT NULL OR `enterprise_id` = 0;

-- 将现有用户的role设为consumer
UPDATE `users` SET `role` = 'consumer' WHERE `role` IS NULL;

-- 将现有用户的status转换为新的ENUM值
-- 假设原来的状态：0=待审核, 1=启用, 2=禁用
-- 新的状态：pending_approval, active, rejected, suspended
UPDATE `users` SET `status` = 'pending_approval' WHERE `status` = 0;
UPDATE `users` SET `status` = 'active' WHERE `status` = 1;
UPDATE `users` SET `status` = 'suspended' WHERE `status` = 2;

-- 8. 更新其他表中的外键引用（如果存在）
-- 更新login_log表的外键引用
ALTER TABLE `login_log` DROP FOREIGN KEY IF EXISTS `login_log_ibfk_1`;
ALTER TABLE `login_log` ADD CONSTRAINT `fk_login_log_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- 更新logs表的外键引用（如果存在）
-- ALTER TABLE `logs` DROP FOREIGN KEY IF EXISTS `logs_ibfk_1`;
-- ALTER TABLE `logs` ADD CONSTRAINT `fk_logs_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- 完成迁移
SELECT 'User table migration completed successfully' as message;
