-- =============================================================================
-- 只读查询 — 不修改数据
-- 功能：contacts 有记录但 phones 为空的联系人
-- =============================================================================

SELECT c.id, c.fn, c.fn_pinyin, c.org, c.note
FROM contacts c
LEFT JOIN phones p ON c.id = p.contact_id
WHERE p.contact_id IS NULL
ORDER BY c.fn;
