/*
 Navicat Premium Data Transfer

 Source Server         : ai_serve
 Source Server Type    : MySQL
 Source Server Version : 80025 (8.0.25)
 Source Host           : rm-bp1j5w6xje06c6l5tvo.mysql.rds.aliyuncs.com:3306
 Source Schema         : gx_booking_db

 Target Server Type    : MySQL
 Target Server Version : 80025 (8.0.25)
 File Encoding         : 65001

 Date: 15/07/2025 09:26:31
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for agent
-- ----------------------------
DROP TABLE IF EXISTS `agent`;
CREATE TABLE `agent` (
  `id` int NOT NULL AUTO_INCREMENT,
  `level` varchar(255) NOT NULL,
  `agent_rebate` varchar(255) NOT NULL,
  `direct_students_count` int NOT NULL,
  `student_commission` varchar(255) NOT NULL,
  `rebate` varchar(255) NOT NULL,
  `account` varchar(255) NOT NULL,
  `status` varchar(255) NOT NULL,
  `approvalsNumber` int NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `isTop` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '是否置顶',
  PRIMARY KEY (`id`),
  UNIQUE KEY `IDX_6335cbdf46e80cbdcd0fbaef56` (`account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for agent_data
-- ----------------------------
DROP TABLE IF EXISTS `agent_data`;
CREATE TABLE `agent_data` (
  `id` int NOT NULL AUTO_INCREMENT,
  `agent_id` int NOT NULL,
  `complete_the_task` int DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `accepting_orders` int DEFAULT NULL COMMENT '区间内接单',
  `complete_order` int DEFAULT NULL COMMENT '区间内完成订单',
  `total_completion_order` int DEFAULT NULL COMMENT '完成总订单',
  `commission` int DEFAULT NULL COMMENT '区间内佣金',
  PRIMARY KEY (`id`),
  KEY `FK_agent_id` (`agent_id`),
  CONSTRAINT `FK_agent_id` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=246 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for agents
-- ----------------------------
DROP TABLE IF EXISTS `agents`;
CREATE TABLE `agents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `agent_rebate` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '返佣比例',
  `student_commission` varchar(255) DEFAULT NULL,
  `rebate` varchar(255) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `approvalsNumber` int NOT NULL DEFAULT '0',
  `created_at` timestamp(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` timestamp(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `direct_students_count` int DEFAULT NULL,
  `is_read` int NOT NULL,
  `isDeleted` tinyint(1) DEFAULT '0',
  `historical_number_of_orders` int DEFAULT NULL COMMENT '历史发单数',
  `add_student_number` int DEFAULT NULL COMMENT '新增学员人数',
  `secondary_agents_count` int DEFAULT NULL COMMENT '二级代理人数',
  `approval_time` varchar(255) DEFAULT NULL COMMENT '审批时间',
  `approval_at` timestamp NULL DEFAULT NULL COMMENT '审批时间',
  `isTop` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=383 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for approval_details
-- ----------------------------
DROP TABLE IF EXISTS `approval_details`;
CREATE TABLE `approval_details` (
  `id` varchar(255) DEFAULT NULL COMMENT 'UUID, primary key',
  `approval_id` varchar(255) DEFAULT NULL COMMENT 'UUID, foreign key to approvals',
  `content` json DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for approvals
-- ----------------------------
DROP TABLE IF EXISTS `approvals`;
CREATE TABLE `approvals` (
  `id` int DEFAULT NULL COMMENT 'UUID, primary key',
  `agent_id` int DEFAULT NULL COMMENT 'UUID, foreign key to agents',
  `status` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for customer_services
-- ----------------------------
DROP TABLE IF EXISTS `customer_services`;
CREATE TABLE `customer_services` (
  `id` int DEFAULT NULL COMMENT 'UUID, primary key',
  `name` varchar(255) DEFAULT NULL,
  `history_order_count` int DEFAULT NULL,
  `service_id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for feedbackinfo
-- ----------------------------
DROP TABLE IF EXISTS `feedbackinfo`;
CREATE TABLE `feedbackinfo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `content` text COMMENT '提交的图片地址',
  `name` varchar(255) DEFAULT NULL COMMENT '提交用户的姓名',
  `feedback_img` text COMMENT '反馈信息图片',
  `message` varchar(255) DEFAULT NULL COMMENT '反馈信息',
  `created_at` datetime DEFAULT NULL COMMENT '反馈时间',
  `student_task_id` int DEFAULT NULL COMMENT 'student_task的id',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb3;

-- ----------------------------
-- Table structure for incomes
-- ----------------------------
DROP TABLE IF EXISTS `incomes`;
CREATE TABLE `incomes` (
  `id` varchar(255) DEFAULT NULL COMMENT 'UUID, primary key',
  `student_id` varchar(255) DEFAULT NULL COMMENT 'UUID, foreign key to students',
  `task_id` varchar(255) DEFAULT NULL COMMENT 'UUID, foreign key to tasks)',
  `commission` decimal(10,2) DEFAULT NULL,
  `payment_status` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for info
-- ----------------------------
DROP TABLE IF EXISTS `info`;
CREATE TABLE `info` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `id_card` varchar(255) DEFAULT NULL,
  `phone_number` varchar(255) DEFAULT NULL,
  `bank_card` varchar(255) DEFAULT NULL,
  `account` varchar(255) DEFAULT NULL,
  `initial_password` varchar(255) DEFAULT NULL,
  `avatar_url` varchar(255) DEFAULT NULL,
  `agentId` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK_dccd1d608bf73e0cc12462cca91` (`agentId`),
  CONSTRAINT `FK_dccd1d608bf73e0cc12462cca91` FOREIGN KEY (`agentId`) REFERENCES `agents` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for loans
-- ----------------------------
DROP TABLE IF EXISTS `loans`;
CREATE TABLE `loans` (
  `id` int DEFAULT NULL COMMENT 'UUID, primary key',
  `customer_id` int DEFAULT NULL COMMENT 'UUID, foreign key to customer_services',
  `amount` decimal(10,2) DEFAULT NULL,
  `project` varchar(255) DEFAULT NULL,
  `payer_name` varchar(255) DEFAULT NULL,
  `payer_role` varchar(255) DEFAULT NULL,
  `agent_name` varchar(255) DEFAULT NULL,
  `order_id` int DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for messages
-- ----------------------------
DROP TABLE IF EXISTS `messages`;
CREATE TABLE `messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sender_id` int DEFAULT NULL COMMENT '客服',
  `receiver_id` int DEFAULT NULL COMMENT '用户',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '客服消息内容',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `receiver_content` text COMMENT '用户消息内容',
  `receiver_read` int DEFAULT NULL COMMENT '客服是否已读， 0未读， 1已读',
  `content_read` int DEFAULT NULL COMMENT '用户是否已读， 0未读， 1已读',
  `task_id` int DEFAULT NULL COMMENT '任务id',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=56 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for student
-- ----------------------------
DROP TABLE IF EXISTS `student`;
CREATE TABLE `student` (
  `id` int NOT NULL AUTO_INCREMENT,
  `agentId` int DEFAULT NULL,
  `skills` varchar(255) DEFAULT NULL,
  `order_limit` varchar(255) DEFAULT NULL,
  `order_level` varchar(255) DEFAULT NULL,
  `user_info_id` int DEFAULT NULL,
  `isDeleted` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `user_info_id` (`user_info_id`)
) ENGINE=InnoDB AUTO_INCREMENT=86 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for studenttask
-- ----------------------------
DROP TABLE IF EXISTS `studenttask`;
CREATE TABLE `studenttask` (
  `id` int NOT NULL AUTO_INCREMENT,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '提交的图片地址',
  `name` varchar(255) DEFAULT NULL COMMENT '提交用户的姓名',
  `user_id` int DEFAULT NULL COMMENT '用户ID',
  `task_id` int DEFAULT NULL COMMENT '任务Id',
  `message` varchar(255) DEFAULT NULL COMMENT '反馈信息',
  `feedback_img` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '反馈图片',
  `status` varchar(255) DEFAULT NULL COMMENT '判断当前任务状态',
  `is_read` int DEFAULT NULL COMMENT '客服反馈后判断学员已读未读， 0是未读， 1是已读',
  `created_at` datetime DEFAULT NULL COMMENT '反馈时间',
  `is_new` int DEFAULT NULL COMMENT '是否是最新的\n0 是新的\n1 是旧的',
  `creation_time` varchar(255) DEFAULT NULL COMMENT '创建时间',
  `feedback_msg` varchar(255) DEFAULT NULL COMMENT '反馈信息内容',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for task_feedbacks
-- ----------------------------
DROP TABLE IF EXISTS `task_feedbacks`;
CREATE TABLE `task_feedbacks` (
  `id` varchar(255) DEFAULT NULL COMMENT 'UUID, primary key',
  `task_id` varchar(255) DEFAULT NULL COMMENT 'UUID, foreign key to tasks',
  `feedback_content` text,
  `feedback_images` json DEFAULT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for tasks
-- ----------------------------
DROP TABLE IF EXISTS `tasks`;
CREATE TABLE `tasks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `summary` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '简介',
  `requirement` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '需求',
  `reference_images` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '参考图',
  `source` varchar(255) DEFAULT NULL COMMENT '来源',
  `order_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '订单号',
  `commission` decimal(10,2) DEFAULT NULL COMMENT '佣金',
  `commission_unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '佣金单位',
  `end_date` datetime DEFAULT NULL COMMENT '截止时间',
  `delivery_date` datetime DEFAULT NULL COMMENT '交稿时间',
  `status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '状态',
  `task_style` varchar(255) DEFAULT NULL COMMENT '风格',
  `task_type` varchar(255) DEFAULT NULL COMMENT '类型',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `orders_number` int DEFAULT NULL COMMENT '接单总人数',
  `order_received_number` int DEFAULT NULL COMMENT '已接单人数',
  `founder` varchar(255) DEFAULT NULL COMMENT '创建人',
  `founder_id` int DEFAULT NULL COMMENT '创建id',
  `message` varchar(255) DEFAULT NULL COMMENT '终止任务原因',
  `task_level` varchar(255) DEFAULT NULL COMMENT '任务级别',
  `accepted_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '保存接取任务的用户 ID',
  `payment_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '支付状态\n待支付订单 - 0\n已支付订单 - 1\n待结算订单 - 2\n可结算订单 - 3\n已结算订单 - 4\n终止订单 - 5',
  `accepted_name` text COMMENT '保存接取任务的用户名称',
  `is_renew` varchar(255) DEFAULT NULL COMMENT '任务更新，0未更新， 1更新',
  `is_virtual` tinyint(1) DEFAULT '0' COMMENT '是否为虚拟任务：0-普通任务，1-虚拟任务',
  PRIMARY KEY (`id`),
  KEY `idx_is_virtual` (`is_virtual`)
) ENGINE=InnoDB AUTO_INCREMENT=112 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for tokens
-- ----------------------------
DROP TABLE IF EXISTS `tokens`;
CREATE TABLE `tokens` (
  `id` varchar(255) DEFAULT NULL COMMENT 'UUID, primary key',
  `user_id` varchar(255) DEFAULT NULL COMMENT 'UUID, foreign key to users',
  `token` varchar(255) DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(255) NOT NULL,
  `lastLoginTime` datetime DEFAULT NULL,
  `isDeleted` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=278 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for userinfo
-- ----------------------------
DROP TABLE IF EXISTS `userinfo`;
CREATE TABLE `userinfo` (
  `roleId` int NOT NULL AUTO_INCREMENT,
  `userId` int NOT NULL,
  `studentId` int DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `id_card` varchar(255) DEFAULT NULL,
  `phone_number` varchar(255) DEFAULT NULL,
  `bank_card` varchar(255) DEFAULT NULL,
  `account` varchar(255) DEFAULT NULL,
  `initial_password` varchar(255) DEFAULT NULL,
  `avatar_url` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `agentId` int DEFAULT NULL,
  `level` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '0是管理员，1是一级代理， 2是二级代理，3是学员， 4是企业代理，5是个人代理，-1是商业贷款， -2是个体工商户，',
  `parentId` int NOT NULL DEFAULT '0',
  `isDeleted` tinyint(1) DEFAULT '0',
  `material` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '资料',
  `identityDocs` text COMMENT '身份证/户口本/居住证明',
  `marriageCert` text COMMENT '婚姻状况证明(结婚证或单身证明)',
  `incomeProof` text COMMENT '收入和财产证明',
  `creditReport` text COMMENT '征信报告',
  `houseContract` text COMMENT '购房合同和首付款收据',
  `businessNames` text COMMENT '营业执照名称备选项',
  `operatorName` text COMMENT '经营者姓名',
  `idCardPhotos` text COMMENT '身份证照片',
  `businessScope` text COMMENT '经营范围',
  `business_license` int DEFAULT NULL COMMENT '企业证件号',
  `personal_license` int DEFAULT NULL COMMENT '个人证件号',
  `referralInfo` varchar(255) DEFAULT NULL COMMENT '填写选项（谁推荐或谁的管理下）',
  `packageType` text COMMENT '套餐选项（类型—3999类型二18888类型三0元启动）',
  `needsComputer` text NOT NULL COMMENT '租借电脑选项（是否）',
  `orderChannels` text COMMENT '接单渠道选项（淘宝，抖音，b站，其他）',
  `bank_name` varchar(255) DEFAULT NULL COMMENT '开户行名称',
  PRIMARY KEY (`roleId`),
  KEY `FK_9c6b41f61375bc4bf1e720f2d22` (`agentId`),
  KEY `FK_e8f6ca40d3fde5123760117b37d` (`userId`),
  KEY `studentId` (`studentId`),
  CONSTRAINT `FK_9c6b41f61375bc4bf1e720f2d22` FOREIGN KEY (`agentId`) REFERENCES `agents` (`id`),
  CONSTRAINT `FK_e8f6ca40d3fde5123760117b37d` FOREIGN KEY (`userId`) REFERENCES `user` (`id`),
  CONSTRAINT `userinfo_ibfk_1` FOREIGN KEY (`studentId`) REFERENCES `student` (`user_info_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=289 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for virtual_order_pool
-- ----------------------------
DROP TABLE IF EXISTS `virtual_order_pool`;
CREATE TABLE `virtual_order_pool` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL COMMENT '学生ID，关联userinfo表的roleId',
  `student_name` varchar(255) NOT NULL COMMENT '学生姓名',
  `total_subsidy` decimal(10,2) NOT NULL COMMENT '总补贴金额',
  `remaining_amount` decimal(10,2) NOT NULL COMMENT '剩余可分配金额',
  `allocated_amount` decimal(10,2) DEFAULT '0.00' COMMENT '已分配金额',
  `completed_amount` decimal(10,2) DEFAULT '0.00' COMMENT '已完成任务金额',
  `status` varchar(50) DEFAULT 'active' COMMENT '状态：active-活跃, completed-已完成, expired-已过期',
  `import_batch` varchar(100) DEFAULT NULL COMMENT '导入批次号',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `last_allocation_at` datetime DEFAULT NULL COMMENT '最后分配时间',
  PRIMARY KEY (`id`),
  KEY `idx_student_id` (`student_id`),
  KEY `idx_status` (`status`),
  KEY `idx_import_batch` (`import_batch`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='虚拟订单资金池表';

-- ----------------------------
-- Table structure for virtual_order_reports
-- ----------------------------
DROP TABLE IF EXISTS `virtual_order_reports`;
CREATE TABLE `virtual_order_reports` (
  `id` int NOT NULL AUTO_INCREMENT,
  `report_date` date NOT NULL COMMENT '报表日期',
  `student_id` int NOT NULL COMMENT '学生ID',
  `student_name` varchar(255) NOT NULL COMMENT '学生姓名',
  `total_tasks_generated` int DEFAULT '0' COMMENT '当日生成虚拟任务总数',
  `total_tasks_accepted` int DEFAULT '0' COMMENT '当日接取任务数',
  `total_tasks_completed` int DEFAULT '0' COMMENT '当日完成任务数',
  `total_tasks_expired` int DEFAULT '0' COMMENT '当日过期任务数',
  `total_amount_generated` decimal(10,2) DEFAULT '0.00' COMMENT '当日生成任务总金额',
  `total_amount_accepted` decimal(10,2) DEFAULT '0.00' COMMENT '当日接取任务总金额',
  `total_amount_completed` decimal(10,2) DEFAULT '0.00' COMMENT '当日完成任务总金额',
  `total_amount_expired` decimal(10,2) DEFAULT '0.00' COMMENT '当日过期任务总金额',
  `remaining_subsidy` decimal(10,2) DEFAULT '0.00' COMMENT '剩余补贴金额',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_date` (`student_id`,`report_date`),
  KEY `idx_report_date` (`report_date`),
  KEY `idx_student_id` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='虚拟订单统计报表';

SET FOREIGN_KEY_CHECKS = 1;
-- 创建虚拟客服表
CREATE TABLE `virtual_customer_services` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT '关联的用户ID',
  `name` varchar(255) NOT NULL COMMENT '客服姓名',
  `account` varchar(255) NOT NULL COMMENT '客服账号',
  `initial_password` varchar(255) NOT NULL COMMENT '初始密码',
  `level` varchar(10) NOT NULL DEFAULT '6' COMMENT '客服级别，固定为6',
  `status` varchar(20) NOT NULL DEFAULT 'active' COMMENT '状态：active-活跃, inactive-停用',
  `last_login_time` datetime DEFAULT NULL COMMENT '最后登录时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_account` (`account`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`),
  CONSTRAINT `fk_virtual_cs_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='虚拟客服表';