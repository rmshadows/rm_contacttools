-- =============================================================================
-- 只读查询 — 不修改数据
-- 功能：查重复电话号码（汇总 + 明细）
-- =============================================================================

-- 汇总：每个号码一行
SELECT number, contact_count, contact_ids
FROM v_duplicate_phones
ORDER BY contact_count DESC, number;

-- 明细：每条 phones 行一行（推荐）
SELECT phone_id, contact_id, fn, fn_pinyin, number, types, dup_count
FROM v_duplicate_phone_detail
ORDER BY dup_count DESC, fn_pinyin COLLATE NOCASE, number, phone_id;
