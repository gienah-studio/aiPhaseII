-- 1. 确保组织表有一个默认组织
INSERT INTO organization (id, name, status, create_time) 
VALUES (1, '默认组织', 1, CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE name = '默认组织';

-- 2. 创建根部门
INSERT INTO department (id, name, parent_id, enterprise_id, organization_id, status, create_time)
VALUES (1, '总部', NULL, 1, 1, 1, CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE name = '总部';

-- 3. 创建一个默认企业
INSERT INTO enterprise_info (id, name, identification_code, organization_id, status, create_time)
VALUES (1, '默认企业', 'DEFAULT001', 1, 1, CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE name = '默认企业';

-- 4. 更新admin用户信息 (使用bcrypt哈希后的密码)
UPDATE user 
SET organization_id = 1,
    enterprise_id = 1,
    department_id = 1,
    status = 1,
    user_type = 2,
    password = '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'  -- 这是'123456'的bcrypt哈希值
WHERE account = 'admin';

-- 如果admin用户不存在，则创建 (使用bcrypt哈希后的密码)
INSERT INTO user (name, account, password, status, user_type, organization_id, enterprise_id, department_id, create_time)
SELECT '系统管理员', 'admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 1, 2, 1, 1, 1, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM user WHERE account = 'admin'); 