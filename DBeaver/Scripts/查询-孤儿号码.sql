-- =============================================================================
-- 只读查询 — 不修改数据
-- 功能：phones 有记录，但 contact_id 在 contacts 中找不到（孤儿号码）
-- 正常库在外键 ON DELETE CASCADE 下应为 0 行；若有结果，多为历史脏数据或曾关闭外键
-- =============================================================================

SELECT
    p.id AS phone_id,
    p.contact_id,
    p.number,
    p.types,
    p.pref,
    p.sort_order
FROM phones p
LEFT JOIN contacts c ON c.id = p.contact_id
WHERE c.id IS NULL
ORDER BY p.id;

-- 邮箱同理（可选）
-- SELECT e.id AS email_id, e.contact_id, e.address, e.types, e.sort_order
-- FROM emails e
-- LEFT JOIN contacts c ON c.id = e.contact_id
-- WHERE c.id IS NULL
-- ORDER BY e.id;
