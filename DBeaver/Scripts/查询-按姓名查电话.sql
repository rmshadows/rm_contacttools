-- =============================================================================
-- 只读查询 — 不修改数据
-- 功能：按姓名关键字查某人的全部号码
-- =============================================================================

SELECT c.id, c.fn, c.fn_pinyin, p.id AS phone_id,
       p.number, p.types, p.pref, p.sort_order
FROM contacts c
JOIN phones p ON p.contact_id = c.id
WHERE c.fn LIKE '%关键字%'
ORDER BY c.fn, p.sort_order, p.id;
