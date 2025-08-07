-- 修复模块操作权限配置的SQL脚本

-- 编辑管理员模块 - 只保留查看和编辑权限
DELETE FROM module_operation 
WHERE module_id IN (SELECT id FROM module WHERE name LIKE '%编辑管理员%' OR name LIKE '%edit admin%')
  AND operation_id IN (SELECT id FROM operation WHERE code IN ('add', 'delete'));

-- 确保编辑管理员有查看和编辑权限
INSERT IGNORE INTO module_operation (module_id, operation_id)
SELECT m.id, o.id 
FROM module m 
JOIN operation o ON o.code IN ('view', 'edit')
WHERE (m.name LIKE '%编辑管理员%' OR m.name LIKE '%edit admin%');

-- 新增管理员模块 - 只保留查看和新增权限
DELETE FROM module_operation 
WHERE module_id IN (SELECT id FROM module WHERE name LIKE '%新增管理员%' OR name LIKE '%add admin%')
  AND operation_id IN (SELECT id FROM operation WHERE code IN ('edit', 'delete'));

-- 确保新增管理员有查看和新增权限
INSERT IGNORE INTO module_operation (module_id, operation_id)
SELECT m.id, o.id 
FROM module m 
JOIN operation o ON o.code IN ('view', 'add')
WHERE (m.name LIKE '%新增管理员%' OR m.name LIKE '%add admin%');

-- 编辑权限组模块 - 只保留查看和编辑权限
DELETE FROM module_operation 
WHERE module_id IN (SELECT id FROM module WHERE name LIKE '%编辑权限组%' OR name LIKE '%edit permission%')
  AND operation_id IN (SELECT id FROM operation WHERE code IN ('add', 'delete'));

-- 确保编辑权限组有查看和编辑权限
INSERT IGNORE INTO module_operation (module_id, operation_id)
SELECT m.id, o.id 
FROM module m 
JOIN operation o ON o.code IN ('view', 'edit')
WHERE (m.name LIKE '%编辑权限组%' OR m.name LIKE '%edit permission%');

-- 新增权限组模块 - 只保留查看和新增权限
DELETE FROM module_operation 
WHERE module_id IN (SELECT id FROM module WHERE name LIKE '%新增权限组%' OR name LIKE '%add permission%')
  AND operation_id IN (SELECT id FROM operation WHERE code IN ('edit', 'delete'));

-- 确保新增权限组有查看和新增权限
INSERT IGNORE INTO module_operation (module_id, operation_id)
SELECT m.id, o.id 
FROM module m 
JOIN operation o ON o.code IN ('view', 'add')
WHERE (m.name LIKE '%新增权限组%' OR m.name LIKE '%add permission%');

-- 处理其他可能的模块
-- 将所有包含"编辑"名称的模块设置为只有查看和编辑权限
DELETE FROM module_operation 
WHERE module_id IN (SELECT id FROM module WHERE (name LIKE '%编辑%' OR name LIKE '%edit%') 
                    AND id NOT IN (SELECT module_id FROM module_operation 
                                  WHERE operation_id IN (SELECT id FROM operation WHERE code IN ('view', 'edit'))))
  AND operation_id IN (SELECT id FROM operation WHERE code IN ('add', 'delete'));

-- 将所有包含"新增"名称的模块设置为只有查看和新增权限
DELETE FROM module_operation 
WHERE module_id IN (SELECT id FROM module WHERE (name LIKE '%新增%' OR name LIKE '%add%' OR name LIKE '%create%') 
                   AND id NOT IN (SELECT module_id FROM module_operation 
                                 WHERE operation_id IN (SELECT id FROM operation WHERE code IN ('view', 'add'))))
  AND operation_id IN (SELECT id FROM operation WHERE code IN ('edit', 'delete')); 