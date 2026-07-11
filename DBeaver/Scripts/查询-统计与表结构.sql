-- =============================================================================
-- 只读查询 — 不修改数据
-- 功能：统计条数、查看表与字段结构
-- =============================================================================

SELECT COUNT(*) AS 联系人数 FROM contacts;

SELECT name AS 表名
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;

PRAGMA table_info(contacts);
PRAGMA table_info(phones);
PRAGMA table_info(emails);
