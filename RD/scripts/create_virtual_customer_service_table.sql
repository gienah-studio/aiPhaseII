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
