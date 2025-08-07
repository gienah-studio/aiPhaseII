-- 为tasks表添加target_student_id字段
-- 用于限制虚拟任务只能被指定的学生接取
-- 此字段只对虚拟任务有效，不影响普通任务的流程

ALTER TABLE `tasks` 
ADD COLUMN `target_student_id` int DEFAULT NULL COMMENT '目标学生ID，虚拟任务专用，限制只有指定学生可以接取' 
AFTER `is_virtual`;

-- 添加索引以提高查询性能
ALTER TABLE `tasks` 
ADD INDEX `idx_target_student_id` (`target_student_id`);

-- 添加复合索引，用于快速查询某个学生的虚拟任务
ALTER TABLE `tasks` 
ADD INDEX `idx_virtual_target_student` (`is_virtual`, `target_student_id`);
